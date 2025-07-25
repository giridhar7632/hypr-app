"use client"
import { ReactLenis } from 'lenis/react'
import TextReveal from '@/components/TextReveal';


export default function Info() {
    
    
    return (
        <ReactLenis root>
        <div className="info w-screen min-h-screen flex items-center justify-center">
            <div className="col">
                <img src="globe.svg" alt="globe" />
            </div>
            <div className="col">
                <TextReveal delay={1}><p className="font-semibold text-lg">Sentiment analysis is a natural language processing technique used to determine the emotional tone behind text data.
                    It identifies whether content is positive, negative, or neutral, helping systems understand human opinions. This is especially valuable in areas like finance, where investor sentiment can influence market trends.
                    By analyzing news, social media, and reports, sentiment analysis turns raw language into actionable insights.</p></TextReveal>
            </div>
        </div>
        </ReactLenis>
    );
}