import React from 'react'

/**
 * EliminatedOverlay
 * Rendered inside .central-panel for any tab but Settings once a player
 * is confirmed dead — same slot FlightOverlay/CitadelOverlay occupy for
 * their respective blocked states.
 */
export function EliminatedOverlay() {
    return (
        <div className="eliminated-overlay">
            <div className="eliminated-overlay-info">
                <div className="eliminated-overlay-icon">†</div>
                <div className="eliminated-overlay-title">OPERATIVE DECEASED</div>
                <div className="eliminated-overlay-subtitle">
                    This section is no longer available. Settings remains reachable.
                </div>
            </div>
        </div>
    )
}

/**
 * EliminatedModal
 * Shown once, at the moment a real-time elimination event arrives for the
 * logged-in player. Rendered as a sibling to the graying dashboard, so it
 * stays interactive regardless of the dead-state pointer-events rules.
 */
export function EliminatedModal({ onClose }) {
    return (
        <div className="profile-backdrop" onClick={onClose}>
            <div className="eliminated-modal" onClick={e => e.stopPropagation()}>
                <div className="eliminated-modal-icon">†</div>
                <h3 className="eliminated-modal-title">You have been eliminated</h3>
                <p className="eliminated-modal-text">
                    If you have not done so yet, set an email address from the Settings
                    page to receive a boost on your next account.
                </p>
                <button className="btn-profile ghost" onClick={onClose}>Close</button>
            </div>
        </div>
    )
}
