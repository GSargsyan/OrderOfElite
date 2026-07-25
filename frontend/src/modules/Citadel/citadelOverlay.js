import React, { useState, useEffect, useContext } from 'react'
import { UserPreviewCtx } from 'modules/Dashboard'
import { LeaveCitadelButton, formatCitadelCountdown } from 'modules/Citadel/citadelTab'

/**
 * CitadelOverlay
 * Rendered inside .central-panel when the user is inside the Citadel
 * and opens a blocked tab. Shows the time left and a departure button.
 */
function CitadelOverlay() {
    const { userPreviewData, updateUserPreviewData } = useContext(UserPreviewCtx)
    const citadelData = userPreviewData?.citadel_data

    const [countdown, setCountdown] = useState(() => {
        if (!citadelData) return 0
        return Math.max(0, Math.floor(citadelData.stay_until - Date.now() / 1000))
    })

    useEffect(() => {
        if (!citadelData) return

        const interval = setInterval(() => {
            const remaining = Math.max(0, Math.floor(citadelData.stay_until - Date.now() / 1000))
            setCountdown(remaining)
            if (remaining === 0) {
                clearInterval(interval)
                // Stay expired — refresh preview so the tabs unlock
                setTimeout(() => updateUserPreviewData(), 1500)
            }
        }, 1000)

        return () => clearInterval(interval)
    }, [citadelData, updateUserPreviewData])

    return (
        <div className="citadel-overlay">
            <div className="citadel-overlay-info">
                <div className="citadel-overlay-icon">🏛</div>
                <div className="citadel-overlay-title">SANCTUARY IN EFFECT</div>
                <div className="citadel-overlay-eta">
                    <span className="citadel-overlay-eta-label">UNTIL DEPARTURE</span>
                    <span className="citadel-overlay-eta-value">
                        {countdown > 0 ? formatCitadelCountdown(countdown) : 'Doors opening...'}
                    </span>
                </div>
                <div className="citadel-overlay-subtitle">
                    No business shall be conducted on Citadel grounds.
                    This section remains sealed until departure.
                </div>
                <LeaveCitadelButton onLeft={() => updateUserPreviewData()} />
            </div>
        </div>
    )
}

export default CitadelOverlay
