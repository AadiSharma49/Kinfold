export function FaqItem({
  question,
  answer,
}: {
  question: string;
  answer: string;
}) {
  return (
    <details className="group border-b border-border py-4 [&_summary::-webkit-details-marker]:hidden">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-medium">
        {question}
        <span
          aria-hidden="true"
          className="shrink-0 text-muted-foreground transition-transform group-open:rotate-45"
        >
          +
        </span>
      </summary>
      <p className="mt-3 text-muted-foreground">{answer}</p>
    </details>
  );
}
