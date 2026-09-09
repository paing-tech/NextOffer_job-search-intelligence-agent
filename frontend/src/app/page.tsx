import Chat from '@/components/chat';
import { requireUser } from '@/lib/supabase/require-user';

export default async function ChatPage() {
  await requireUser();
  return <Chat />;
}
