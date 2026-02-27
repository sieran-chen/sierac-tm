package com.cursor.hook;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

/**
 * Cursor Hook（Java）
 * - beforeSubmitPrompt: 白名单校验（未匹配则拦截）+ 记录会话开始与 project_id
 * - stop: 上报会话结束 + workspace_roots + 时长 + project_id
 *
 * 运行方式：从 stdin 读入一行 JSON，向 stdout 输出 {"continue":true} 或 {"continue":false,"message":"..."}
 * 部署：~/.cursor/hooks/cursor_hook.jar + hook_config.json（支持 whitelist_ttl_seconds、whitelist_enabled、project_id）
 */
public final class CursorHook {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final boolean IS_WINDOWS = System.getProperty("os.name", "").toLowerCase(java.util.Locale.ROOT).startsWith("win");

    public static void main(String[] args) {
        try {
            if (!run()) {
                return; // already output block message
            }
        } catch (Throwable t) {
            // 任何异常都不影响 Cursor，只输出放行
        }
        outputContinue();
    }

    /** @return false if we already wrote a block response (do not call outputContinue) */
    private static boolean run() throws IOException {
        String raw = readStdin();
        if (raw == null || raw.isBlank()) {
            return true;
        }
        JsonNode event = JSON.readTree(raw);
        String eventName = text(event, "hook_event_name");
        String conversationId = text(event, "conversation_id");
        List<String> workspaceRoots = stringList(event, "workspace_roots");
        long nowSec = System.currentTimeMillis() / 1000;

        Path hooksDir = resolveHooksDir();
        Config config = loadConfig(hooksDir);

        if ("beforeSubmitPrompt".equals(eventName)) {
            Integer projectId = null;
            if (config.whitelistEnabled) {
                List<JsonNode> rules = getWhitelist(config);
                if (rules != null) {
                    JsonNode matched = matchWhitelist(workspaceRoots, config.userEmail, rules);
                    if (matched == null) {
                        String msg = "\u26d4 当前工作目录未在公司项目白名单中。请联系管理员在 Sierac 平台完成项目立项后再使用企业 Cursor。\n当前目录: " + workspaceRoots;
                        outputBlock(msg);
                        return false;
                    }
                    if (matched.has("project_id") && !matched.get("project_id").isNull()) {
                        projectId = matched.get("project_id").asInt();
                    }
                }
                // fail-open: rules == null (network error) -> allow
            }
            if (conversationId != null && !conversationId.isEmpty()) {
                saveSessionStart(config.stateDir, conversationId, workspaceRoots, nowSec, projectId);
            }
            return true;
        }

        if ("stop".equals(eventName)) {
            Integer durationSeconds = null;
            Integer projectId = null;
            if (conversationId != null && !conversationId.isEmpty()) {
                SessionStart start = loadSessionStart(config.stateDir, conversationId);
                if (start != null) {
                    durationSeconds = (int) (nowSec - start.startedAt);
                    projectId = start.projectId;
                    if (workspaceRoots.isEmpty() && start.workspaceRoots != null) {
                        workspaceRoots = start.workspaceRoots;
                    }
                    deleteSessionStart(config.stateDir, conversationId);
                }
            }
            ObjectNode payload = JSON.createObjectNode()
                .put("event", "session_end")
                .put("conversation_id", conversationId != null ? conversationId : "")
                .put("user_email", config.userEmail)
                .put("machine_id", config.machineId)
                .put("ended_at", (int) nowSec);
            if (durationSeconds != null) {
                payload.put("duration_seconds", durationSeconds);
            }
            if (projectId != null) {
                payload.put("project_id", projectId);
            }
            ArrayNode arr = payload.putArray("workspace_roots");
            for (String r : workspaceRoots) {
                arr.add(r);
            }
            postSession(config.collectorUrl, payload, config.timeoutSeconds);
        }
        return true;
    }

    private static void outputBlock(String message) {
        try {
            ObjectNode o = JSON.createObjectNode().put("continue", false).put("message", message);
            System.out.println(o.toString());
        } catch (Exception ignored) {
        }
    }

    private static String readStdin() throws IOException {
        InputStream in = System.in;
        StringBuilder sb = new StringBuilder();
        byte[] buf = new byte[8192];
        int n;
        while ((n = in.read(buf)) >= 0) {
            sb.append(new String(buf, 0, n, StandardCharsets.UTF_8));
        }
        return sb.toString().trim();
    }

    private static void outputContinue() {
        try {
            System.out.println("{\"continue\":true}");
        } catch (Exception ignored) {
        }
    }

    private static String text(JsonNode node, String key) {
        JsonNode v = node != null ? node.get(key) : null;
        return v != null && v.isTextual() ? v.asText() : "";
    }

    private static List<String> stringList(JsonNode node, String key) {
        List<String> out = new ArrayList<>();
        JsonNode arr = node != null ? node.get(key) : null;
        if (arr != null && arr.isArray()) {
            for (JsonNode e : arr) {
                if (e != null && e.isTextual()) {
                    out.add(e.asText());
                }
            }
        }
        return out;
    }

    private static Path resolveHooksDir() {
        String home = System.getProperty("user.home");
        if (home == null) {
            home = System.getenv("USERPROFILE");
        }
        if (home == null) {
            home = System.getenv("HOME");
        }
        if (home == null) {
            home = ".";
        }
        return Paths.get(home, ".cursor", "hooks");
    }

    private static Config loadConfig(Path hooksDir) throws IOException {
        Path configPath = hooksDir.resolve("hook_config.json");
        Config c = new Config();
        c.collectorUrl = "http://localhost:8000";
        c.userEmail = "";
        c.machineId = "";
        c.timeoutSeconds = 5;
        c.stateDir = hooksDir.resolve(".state").toString();

        String emailFromEnv = System.getenv("CURSOR_USER_EMAIL");
        if (emailFromEnv == null) emailFromEnv = System.getenv("GIT_AUTHOR_EMAIL");
        if (emailFromEnv == null) emailFromEnv = System.getenv("EMAIL");
        if (emailFromEnv != null && !emailFromEnv.isBlank()) {
            c.userEmail = emailFromEnv.trim();
        }
        String user = System.getenv("USER");
        if (user == null) user = System.getenv("USERNAME");
        if (user == null) user = "unknown";
        if (c.userEmail.isEmpty()) {
            c.userEmail = user;
        }

        if (Files.isRegularFile(configPath)) {
            try {
                JsonNode cfg = JSON.readTree(configPath.toFile());
                if (cfg.has("collector_url")) c.collectorUrl = cfg.get("collector_url").asText();
                if (cfg.has("user_email") && !cfg.get("user_email").asText().isEmpty()) {
                    c.userEmail = cfg.get("user_email").asText();
                }
                if (cfg.has("machine_id") && !cfg.get("machine_id").asText().isEmpty()) {
                    c.machineId = cfg.get("machine_id").asText();
                }
                if (cfg.has("timeout_seconds")) c.timeoutSeconds = cfg.get("timeout_seconds").asInt(5);
                if (cfg.has("state_dir") && !cfg.get("state_dir").asText().isEmpty()) {
                    c.stateDir = cfg.get("state_dir").asText();
                }
                if (cfg.has("whitelist_ttl_seconds")) c.whitelistTtlSeconds = cfg.get("whitelist_ttl_seconds").asInt(300);
                if (cfg.has("whitelist_enabled")) c.whitelistEnabled = cfg.get("whitelist_enabled").asBoolean(true);
            } catch (Exception ignored) {
            }
        }

        if (c.machineId.isEmpty()) {
            String raw = System.getProperty("os.name", "") + System.getProperty("user.name", "");
            try {
                MessageDigest md = MessageDigest.getInstance("MD5");
                byte[] digest = md.digest(raw.getBytes(StandardCharsets.UTF_8));
                StringBuilder sb = new StringBuilder("m-");
                for (int i = 0; i < 6 && i * 2 < digest.length; i++) {
                    sb.append(String.format("%02x", digest[i]));
                }
                c.machineId = sb.toString();
            } catch (Exception e) {
                c.machineId = "m-" + raw.hashCode();
            }
        }
        return c;
    }

    private static final class Config {
        String collectorUrl;
        String userEmail;
        String machineId;
        int timeoutSeconds;
        String stateDir;
        int whitelistTtlSeconds = 300;
        boolean whitelistEnabled = true;
    }

    // ----- 本地状态 -----

    private static Path stateFile(String stateDir, String conversationId) {
        String safe = conversationId.replace("/", "_").replace("\\", "_");
        return Paths.get(stateDir, safe + ".json");
    }

    private static void saveSessionStart(String stateDir, String conversationId, List<String> workspaceRoots, long startedAt, Integer projectId) {
        try {
            Files.createDirectories(Paths.get(stateDir));
            ObjectNode o = JSON.createObjectNode().put("started_at", startedAt);
            if (projectId != null) o.put("project_id", projectId);
            ArrayNode arr = o.putArray("workspace_roots");
            for (String r : workspaceRoots) {
                arr.add(r);
            }
            Files.writeString(stateFile(stateDir, conversationId), o.toString(), StandardCharsets.UTF_8);
        } catch (Exception ignored) {
        }
    }

    private static SessionStart loadSessionStart(String stateDir, String conversationId) {
        Path p = stateFile(stateDir, conversationId);
        if (!Files.isRegularFile(p)) return null;
        try {
            JsonNode n = JSON.readTree(Files.readString(p, StandardCharsets.UTF_8));
            SessionStart s = new SessionStart();
            s.startedAt = n.has("started_at") ? n.get("started_at").asLong() : 0;
            s.workspaceRoots = stringList(n, "workspace_roots");
            s.projectId = n.has("project_id") && !n.get("project_id").isNull() ? n.get("project_id").asInt() : null;
            return s;
        } catch (Exception e) {
            return null;
        }
    }

    private static void deleteSessionStart(String stateDir, String conversationId) {
        try {
            Files.deleteIfExists(stateFile(stateDir, conversationId));
        } catch (Exception ignored) {
        }
    }

    private static final class SessionStart {
        long startedAt;
        List<String> workspaceRoots;
        Integer projectId;
    }

    // ----- Whitelist (cache + fetch + match, fail-open) -----

    private static Path whitelistCachePath(String stateDir) {
        return Paths.get(stateDir, "whitelist_cache.json");
    }

    private static List<JsonNode> loadWhitelistCache(String stateDir, int ttlSeconds) {
        Path p = whitelistCachePath(stateDir);
        if (!Files.isRegularFile(p)) return null;
        try {
            JsonNode cached = JSON.readTree(Files.readString(p, StandardCharsets.UTF_8));
            long fetchedAt = cached.has("fetched_at") ? cached.get("fetched_at").asLong() : 0;
            if (System.currentTimeMillis() / 1000 - fetchedAt >= ttlSeconds) return null;
            JsonNode rules = cached.get("rules");
            if (rules == null || !rules.isArray()) return null;
            List<JsonNode> out = new ArrayList<>();
            rules.forEach(out::add);
            return out;
        } catch (Exception e) {
            return null;
        }
    }

    private static List<JsonNode> fetchWhitelist(String collectorUrl, int timeoutSeconds) {
        String url = collectorUrl.replaceAll("/+$", "") + "/api/projects/whitelist";
        try {
            HttpClient client = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(timeoutSeconds))
                .build();
            HttpRequest req = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Accept", "application/json")
                .timeout(Duration.ofSeconds(timeoutSeconds))
                .GET()
                .build();
            HttpResponse<String> resp = client.send(req, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
            if (resp.statusCode() != 200) return null;
            JsonNode body = JSON.readTree(resp.body());
            JsonNode rules = body.get("rules");
            if (rules == null || !rules.isArray()) return null;
            List<JsonNode> out = new ArrayList<>();
            rules.forEach(out::add);
            return out;
        } catch (Exception e) {
            return null;
        }
    }

    private static void saveWhitelistCache(String stateDir, List<JsonNode> rules) {
        try {
            Files.createDirectories(Paths.get(stateDir));
            ObjectNode root = JSON.createObjectNode().put("fetched_at", System.currentTimeMillis() / 1000);
            ArrayNode arr = root.putArray("rules");
            for (JsonNode r : rules) arr.add(r);
            Files.writeString(whitelistCachePath(stateDir), root.toString(), StandardCharsets.UTF_8);
        } catch (Exception ignored) {
        }
    }

    private static List<JsonNode> getWhitelist(Config config) {
        List<JsonNode> rules = loadWhitelistCache(config.stateDir, config.whitelistTtlSeconds);
        if (rules != null) return rules;
        rules = fetchWhitelist(config.collectorUrl, config.timeoutSeconds);
        if (rules != null) saveWhitelistCache(config.stateDir, rules);
        return rules;
    }

    private static JsonNode matchWhitelist(List<String> workspaceRoots, String userEmail, List<JsonNode> rules) {
        String userLower = userEmail == null ? "" : userEmail.toLowerCase(java.util.Locale.ROOT);
        for (JsonNode rule : rules) {
            List<String> rulePaths = stringList(rule, "workspace_rules");
            List<String> memberEmails = stringList(rule, "member_emails");
            for (String root : workspaceRoots) {
                for (String rulePath : rulePaths) {
                    boolean matched = IS_WINDOWS
                        ? root.toLowerCase(java.util.Locale.ROOT).startsWith(rulePath.toLowerCase(java.util.Locale.ROOT))
                        : root.startsWith(rulePath);
                    if (!matched) continue;
                    if (!memberEmails.isEmpty()) {
                        boolean inList = false;
                        for (String e : memberEmails) {
                            if (e != null && e.toLowerCase(java.util.Locale.ROOT).equals(userLower)) {
                                inList = true;
                                break;
                            }
                        }
                        if (!inList) continue;
                    }
                    return rule;
                }
            }
        }
        return null;
    }

    // ----- HTTP 上报 -----

    private static void postSession(String collectorUrl, ObjectNode payload, int timeoutSeconds) {
        String url = collectorUrl.replaceAll("/+$", "") + "/api/sessions";
        try {
            HttpClient client = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(timeoutSeconds))
                .build();
            HttpRequest req = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Content-Type", "application/json")
                .timeout(Duration.ofSeconds(timeoutSeconds))
                .POST(HttpRequest.BodyPublishers.ofString(payload.toString(), StandardCharsets.UTF_8))
                .build();
            client.send(req, HttpResponse.BodyHandlers.discarding());
        } catch (Exception ignored) {
            // 静默失败，不影响 Cursor
        }
    }
}
