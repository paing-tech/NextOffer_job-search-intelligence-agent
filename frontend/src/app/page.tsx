import { Suspense } from "react";
import Chat from "@/components/chat";
import { requireUser } from "@/lib/session";

export default async function ChatPage() {
  await requireUser();
  return (
    <Suspense>
      <Chat />
    </Suspense>
  );
}
