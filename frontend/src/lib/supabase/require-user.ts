import { redirect } from 'next/navigation';
import { createClient } from './server';

export async function requireUser() {
  const client = await createClient();
  const { data, error } = await client.auth.getUser();
  if (error || !data.user) redirect('/login');
  return data.user;
}
