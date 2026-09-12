import type { SVGProps } from "react";

// Animated "draw-in" filter icon (Material Line Icons, MIT). The stroke lines
// animate in on mount via SMIL <animate>; since that only plays once per
// mount, the caller replays it by changing `key` to force a remount (see
// ApplicationsFilter in shell.tsx).
export function FilterAltIcon({ size = 24, ...props }: SVGProps<SVGSVGElement> & { size?: number }) {
  return (
    <svg width={size} height={size} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {...props}>
      <g fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5">
        <path strokeDasharray="18" strokeDashoffset="18" d="M4 7h16">
          <animate fill="freeze" attributeName="stroke-dashoffset" dur="0.3s" values="18;0" />
        </path>
        <path strokeDasharray="12" strokeDashoffset="12" d="M7 12h10">
          <animate fill="freeze" attributeName="stroke-dashoffset" begin="0.3s" dur="0.2s" to="0" />
        </path>
        <path strokeDasharray="4" strokeDashoffset="4" d="M11 17h2">
          <animate fill="freeze" attributeName="stroke-dashoffset" begin="0.5s" dur="0.2s" to="0" />
        </path>
      </g>
    </svg>
  );
}
