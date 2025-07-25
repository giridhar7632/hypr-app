"use client"

import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import React, { useRef } from "react";
import {SplitText} from "gsap/SplitText";
import {ScrollTrigger} from "gsap/ScrollTrigger";

gsap.registerPlugin(SplitText, ScrollTrigger);

export default function TextReveal({ children, className, animateOnScroll = true, start, delay = 0 }: { children: React.ReactElement, className?: string, animateOnScroll?: boolean, start?: string, delay?: number }) {
    const containerRef = useRef<HTMLDivElement>(null)
    const elementRef = useRef<any>([])
    const splitRef = useRef<any>([])
    const lineRef = useRef<any>([])

    useGSAP(() => {
        if(!containerRef.current) return
        splitRef.current = []
        elementRef.current = []
        lineRef.current = []

        let elements = []
        if(containerRef.current.hasAttribute("data-copy-wrapper")) {
            elements = Array.from(containerRef.current.children)
        } else {
            elements = [containerRef.current]
        }

        elements.forEach(element => {
            elementRef.current.push(element)
            const split = new SplitText(element, { type: "lines", mask: "lines", lineClass: "line++" })
            splitRef.current.push(split)

            const computedStyle = window.getComputedStyle(element)
            const textIndent = computedStyle.textIndent
            if(textIndent && textIndent !== "0px") {
                if(split.lines.length > 0) {
                    (split.lines[0] as HTMLElement).style.paddingLeft = textIndent

                }
                (element as HTMLElement).style.textIndent = "0px"
            }


            lineRef.current.push(...split.lines)
        })

        gsap.set(lineRef.current, { opacity: 0, y: "100%" })

        const animationProps = {
            opacity: 1,
            y: 0,
            duration: 1,
            ease: "power4.out",
            stagger: 0.1,
            delay: delay
        }

        if(animateOnScroll) {
            gsap.to(lineRef.current, {
                ...animationProps,
                scrollTrigger: {
                    trigger: containerRef.current,
                    start: start || "top 75%",
                    once: true
                }
            })
        } else {
            gsap.to(lineRef.current, animationProps)
        }

        return () => {
            if(splitRef.current) splitRef.current.forEach((split: any) => split.revert())
        }
    }, { scope: containerRef, dependencies: [animateOnScroll, delay, start] })
    
    if(React.Children.count(children) === 1) {
        return React.cloneElement(children, { ref: containerRef, className: `container ${className}` })
    }

    return (
        <div ref={containerRef} data-copy-wrapper="true" className={`container ${className}`}>
            {children}
        </div>
    )
}