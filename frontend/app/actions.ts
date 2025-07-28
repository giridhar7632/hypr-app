'use server'

import { createClient } from '@/lib/supabase'

export async function getLiveQuotes() {
    const supabase = await createClient()
    const { data, error } = await supabase.from('live_quotes').select('*')
    if(error) {
        console.error(error)
        return []
    }
    return data
}

export async function getQuoteData(ticker: string) {
    const supabase = await createClient()
    const { data, error } = await supabase.from('data').select('*').eq('ticker', ticker).limit(1)
    if(error) {
        console.error(error)
        return null
    } else if (!data || data.length === 0) {
        return null
    }

    return data[0]
}
    