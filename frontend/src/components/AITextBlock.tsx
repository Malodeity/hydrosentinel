interface AITextBlockProps {
  label: string;
  content?: string | null;
  items?: string[];
}

const aiBlockStyle = {
  borderLeft: "3px solid #7F77DD",
  background: "var(--color-background-secondary, rgba(226, 232, 240, 0.55))",
  borderRadius: "var(--border-radius-md, 0.75rem)",
  padding: "10px 12px",
} as const;

export function AITextBlock({ label, content, items }: AITextBlockProps) {
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
        <p className="text-sm leading-6 text-foreground">{content}</p>
      )}
    </div>
  );
}
