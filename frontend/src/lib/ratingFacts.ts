import type { WSA } from "@/api/wsa";
import { BLUE_DROP_BAND_TEXT, blueDropBand } from "@/lib/overviewStats";
import { dataCompleteness } from "@/lib/dataCompleteness";

// Plain facts about an authority that sit behind its risk level, for the public card. Every line is read straight from the stored
// data (nothing is inferred), so the card can say what the rating rests on without making claims the data does not support.
export function ratingFacts(wsa: WSA): string[] {
  const facts: string[] = [];
  const band = blueDropBand(wsa.blue_drop_score);
  if (band === "unknown") facts.push("No Blue Drop drinking-water score is recorded, so the rating is less reliable.");
  else facts.push(`Blue Drop score ${wsa.blue_drop_score!.toFixed(1)} is in the ${BLUE_DROP_BAND_TEXT[band].toLowerCase()} band (certification needs 95).`);

  if (wsa.cap_status === "none") facts.push("No corrective action plan has been submitted.");
  else if (wsa.cap_status === "completed") facts.push("Its corrective action plan is complete.");
  else facts.push(`Its corrective action plan is ${wsa.cap_status.replace("_", " ")}.`);

  if (wsa.nrw_percent !== null) facts.push(`${wsa.nrw_percent}% of the water it treats is lost before billing (non-revenue water).`);
  else if (wsa.nrw_estimate_percent != null) facts.push(`Its own water-loss figure is not reported. Its province averages about ${wsa.nrw_estimate_percent}% non-revenue water (DWS 2020/21), shown as an estimate and not used in the rating.`);

  const { filled, total } = dataCompleteness(wsa);
  if (filled < total) facts.push(`Only ${filled} of ${total} key indicators are available for this authority.`);
  return facts;
}
