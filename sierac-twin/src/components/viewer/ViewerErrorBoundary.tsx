import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: () => void;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export default class ViewerErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(): void {
    this.props.onError?.();
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="flex h-full w-full flex-col items-center justify-center gap-2 rounded-lg bg-gray-900/90 p-6 text-center text-sm text-gray-400">
          <p>3D 图片加载失败</p>
          <p className="text-xs">
            请将 14 张视角图放入 <code className="rounded bg-gray-800 px-1">public/images/</code>，参见目录下 README
          </p>
          <p className="text-xs text-gray-500">拖拽与缩放控件仍可用，右侧数据面板正常显示</p>
        </div>
      );
    }
    return this.props.children;
  }
}
