import { Badge, Card } from "@/components/ui";
import { STYLE_LABELS, type Style } from "@/lib/types";

const STYLE_TONES: Record<Style, "primary" | "warn" | "ok" | "neutral"> = {
  formal: "primary",
  sarcastic: "warn",
  humorous_tech: "ok",
  humorous_non_tech: "neutral",
};

export function CaptionCard({ style, text }: { style: Style; text: string }) {
  return (
    <Card className="fade-up">
      <div className="mb-2 flex items-center justify-between">
        <Badge tone={STYLE_TONES[style]}>{STYLE_LABELS[style]}</Badge>
      </div>
      <p className="text-sm leading-relaxed text-foreground/90">{text}</p>
    </Card>
  );
}
