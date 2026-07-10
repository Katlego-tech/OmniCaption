/* eslint-disable @next/next/no-img-element */
/** Icons8 icon — the app's only icon source (free tier, attribution required).
 *
 * All visual icons come from https://icons8.com/icons via their CDN
 * (`img.icons8.com`), per team decision. Keep the "Icons by Icons8" links in
 * the landing footer and sidebar — they are the license's attribution
 * requirement, not decoration.
 */

export const ICONS8_ATTRIBUTION_URL = "https://icons8.com";

export function Icon({
  name,
  size = 18,
  color = "9b9ba6",
  alt = "",
}: {
  name: string;
  size?: number;
  color?: string;
  alt?: string;
}) {
  return (
    <img
      src={`https://img.icons8.com/ios-glyphs/${size * 2}/${color}/${name}.png`}
      width={size}
      height={size}
      alt={alt}
      aria-hidden={alt === ""}
      loading="lazy"
    />
  );
}
