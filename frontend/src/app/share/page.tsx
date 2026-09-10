import { requireUser } from "@/lib/session";
import { ShareIntake } from "@/components/share-intake";

// Web Share Target lands here: the OS passes ?title=&text=&url= from the app the
// user shared from (see public/manifest.webmanifest -> share_target).
export default async function SharePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  await requireUser();
  const params = await searchParams;

  const rawText = (params.text ?? "").trim();
  const explicitUrl = params.url && /^https?:\/\//i.test(params.url) ? params.url : null;
  const urlInText = rawText.match(/https?:\/\/\S+/i)?.[0] ?? null;
  const url = explicitUrl ?? urlInText;

  // If a long block of text came through (not just a link), treat it as the description.
  const leftover = url ? rawText.replace(url, "").trim() : rawText;
  const pastedText = leftover.length > 200 ? leftover : "";

  return <ShareIntake initialUrl={url} initialText={pastedText} sharedTitle={params.title ?? null} />;
}
