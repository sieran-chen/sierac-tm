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
 * Cursor 极简 Hook（Java）
 * - beforeSubmitPrompt: 仅本地记录会话开始时间
 * - stop: 上报会话结束 + workspace_roots + 时长，每次会话 1 条 POST
 *
 * 运行方式：从 stdin 读入一行 JSON，向 stdout 输出 {"continue":true}
 * 部署：~/.cursor/hooks/cursor_hook.jar + hook_config.json
 */
public final class CursorHook {

    private static final ObjectMapper JSON = new ObjectMapper();

    public static void main(String[] args) {
        try {
            run();
        } catch (Throwable t) {
            // 任何异常都不影响 Cursor，只输出放行
        }
        outputContinue();
    }

    private static void run() throws IOException {
        String raw = readStdin();
        if (raw == null || raw.isBlank()) {
            return;
        }
        JsonNode event = JSON.readTree(raw);
        String eventName = text(event, "hook_event_name");
        String conversationId = text(event, "conversation_id");
        List<String> workspaceRoots = stringList(event, "workspace_roots");
        long nowSec = System.currentTimeMillis() / 1000;

        Path hooksDir = resolveHooksDir();
        Config config = loadConfig(hooksDir);

        if ("beforeSubmitPrompt".equals(eventName)) {
            if (conversationId != null && !conversationId.isEmpty()) {
                saveSessionStart(config.stateDir, conversationId, workspaceRoots, nowSec);
            }
            return;
        }

        if ("stop".equals(eventName)) {
            Integer durationSeconds = null;
            if (conversationId != null && !conversationId.isEmpty()) {
                SessionStart start = loadSessionStart(config.stateDir, conversationId);
                if (start != null) {
                    durationSeconds = (int) (nowSec - start.startedAt);
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
            ArrayNode arr = payload.putArray("workspace_roots");
            for (String r : workspaceRoots) {
                arr.add(r);
            }
            postSession(config.collectorUrl, payload, config.timeoutSeconds);
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
    }

    // ----- 本地状态 -----

    private static Path stateFile(String stateDir, String conversationId) {
        String safe = conversationId.replace("/", "_").replace("\\", "_");
        return Paths.get(stateDir, safe + ".json");
    }

    private static void saveSessionStart(String stateDir, String conversationId, List<String> workspaceRoots, long startedAt) {
        try {
            Files.createDirectories(Paths.get(stateDir));
            ObjectNode o = JSON.createObjectNode().put("started_at", startedAt);
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
