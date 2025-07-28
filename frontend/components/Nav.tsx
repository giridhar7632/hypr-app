"use client";

import { useHealthCheck } from "@/hooks/useHealthCheck";
import { slideInOut } from "@/lib/utils";
import { useTransitionRouter } from "next-view-transitions";

export default function Nav() {
    const router = useTransitionRouter()
    const { data: healthCheckData, isLoading: isHealthCheckLoading, isError: isHealthCheckError } = useHealthCheck()
    const turnOnDemoMode = !healthCheckData?.success || isHealthCheckLoading || isHealthCheckError
    
    return (
        <nav className="fixed top-0 left-0 w-screen p-4 z-50">
            <div className="flex justify-between items-center bg-white/50 backdrop-blur-sm w-full p-4 border border-[#eee]/50 rounded-lg">
            <a href="/" className="text-md font-bold">HYPR</a>
            <ul className="flex gap-8 uppercase text-sm p-2">
                {turnOnDemoMode && <p className="text-red-500 text-xs italic normal-case">(Demo Mode)</p>}
                <li><a onClick={(e) => {
                    e.preventDefault()
                    router.push('/', {
                        onTransitionReady: slideInOut
                    })
                }} href="/">Home</a></li>
                <li><a onClick={(e) => {
                    e.preventDefault()
                    router.push('/search', {
                        onTransitionReady: slideInOut
                    })
                }}  href="/search">Search</a></li>
                <li><a onClick={(e) => {
                    e.preventDefault()
                    router.push('/discover', {
                        onTransitionReady: slideInOut
                    })
                }}  href="/discover">Discover</a></li>
            </ul>
            </div>
        </nav>
    );
}