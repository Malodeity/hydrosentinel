// The purple 'AI' box. Every piece of AI-written text in the app is shown through this, so it always looks the same and shows a skeleton while loading.

import { Skeleton } from "@/components/ui/skeleton";

interface AITextBlockProps {
  label: string;
  content?: string | null;
  items?: string[];
  loading?: boolean;
}

const aiBlockStyle = {
  borderLeft: "3px solid #7F77DD",
  background: "var(--color-background-secondary, rgba(226, 232, 240, 0.55))",
  borderRadius: "var(--border-radius-md, 0.75rem)",
  padding: "16px 18px",
} as const;

export function AITextBlock({ label, content, items, loading }: AITextBlockProps) {
  if (loading) {
    // the text comes from a GPT-4o call that takes a few seconds, so say so instead of showing a blank card
    return (
      <div style={aiBlockStyle} aria-busy="true">
        <span className="mb-2 inline-flex rounded-[4px] bg-[#EEEDFE] px-[6px] py-[2px] text-[11px] font-medium text-[#534AB7]">
          {label}
        </span>
        <div className="space-y-2">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-11/12" />
          <Skeleton className="h-3 w-2/3" />
        </div>
      </div>
    );
  }
  if (!content && (!items || items.length === 0)) {
    return null;
  }

  return (
    <div style={aiBlockStyle}>
      <span className="mb-2 inline-flex rounded-[4px] bg-[#EEEDFE] px-[6px] py-[2px] text-[11px] font-medium text-[#534AB7]">
        {label}
      </span>
      {items && items.length > 0 ? (
        <ol className="space-y-2 pl-5 text-sm text-foreground">
          {items.map((item, index) => (
            <li key={`${label}-${index}`}>{item}</li>
          ))}
        </ol>
      ) : (
        <p className="text-sm leading-7 text-foreground">{content}</p>
      )}
    </div>
  );
}
