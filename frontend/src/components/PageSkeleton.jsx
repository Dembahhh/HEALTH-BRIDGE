import Skeleton, { SkeletonTheme } from "react-loading-skeleton";
import "react-loading-skeleton/dist/skeleton.css";
import { useTheme } from "../context/ThemeContext";

export default function PageSkeleton() {
  const style =
    typeof document !== "undefined"
      ? getComputedStyle(document.documentElement)
      : null;
  const baseColor = style
    ? style.getPropertyValue("--bg-elevated").trim()
    : null;
  const highlightColor = style
    ? style.getPropertyValue("--bg-surface").trim()
    : null;

  return (
    <SkeletonTheme baseColor={baseColor} highlightColor={highlightColor}>
      <div style={{ padding: "24px", maxWidth: "800px", margin: "0 auto" }}>
        {/* Page title */}
        <Skeleton
          height={36}
          width="40%"
          style={{ marginBottom: "24px", borderRadius: "8px" }}
        />

        {/* Stats row */}
        <div style={{ display: "flex", gap: "16px", marginBottom: "24px" }}>
          <Skeleton height={80} style={{ flex: 1, borderRadius: "8px" }} />
          <Skeleton height={80} style={{ flex: 1, borderRadius: "8px" }} />
          <Skeleton height={80} style={{ flex: 1, borderRadius: "8px" }} />
        </div>

        {/* Cards */}
        <Skeleton
          height={120}
          style={{ marginBottom: "16px", borderRadius: "8px" }}
        />
        <Skeleton
          height={120}
          style={{ marginBottom: "16px", borderRadius: "8px" }}
        />

        {/* Text lines */}
        <Skeleton count={3} style={{ marginBottom: "8px" }} />
        <Skeleton width="60%" />
      </div>
    </SkeletonTheme>
  );
}
