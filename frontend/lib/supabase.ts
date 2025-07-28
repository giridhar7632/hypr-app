
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

export const createClient = async ( ) => {
    const cookieStore = await cookies()
    return createServerClient(
      supabaseUrl!,
      supabaseKey!,
      {
        cookies: {
          getAll() {
            return cookieStore.getAll();
          },
          setAll(cookiesToSet) {
            try {
              cookiesToSet.forEach(({ name, value, options }) => 
                cookieStore.set(name, value, options)
              );
            } catch {
              // The [setAll](cci:1://file:///Users/giridhartalla/Downloads/01-projects/market-dash/frontend/lib/supabase.ts:16:8-24:9) method was called from a Server Component.
              // This can be ignored if you have middleware refreshing
            }
          }
        }
      }
    );
  };
