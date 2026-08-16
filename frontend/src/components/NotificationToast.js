import React, { useState, useEffect } from 'react'
import socketIOClient from 'socket.io-client'
import { CHAT_SOCKET_PATH, chatSocketUrl } from 'modules/Base/constants.js'

const TOAST_LIFETIME_MS = 7000
const EXIT_ANIMATION_MS = 360 // matches the toastSlideOut keyframe duration

export function NotificationToast() {
    const [toasts, setToasts] = useState([])

    // Two-step removal: mark the toast "leaving" so it plays the slide-out
    // animation, then actually drop it from state once that's done.
    const dismiss = (toastId) => {
        setToasts(prev => prev.map(t => t.toastId === toastId ? { ...t, leaving: true } : t))
        setTimeout(() => {
            setToasts(prev => prev.filter(t => t.toastId !== toastId))
        }, EXIT_ANIMATION_MS)
    }

    useEffect(() => {
        const token = localStorage.getItem('token')
        const socket = socketIOClient(chatSocketUrl('/notifications'), {
            path: CHAT_SOCKET_PATH,
            query: { token },
            forceNew: true,
        })

        socket.on('new_notification', (data) => {
            const toastId = `${data.id ?? 'toast'}-${Date.now()}`
            setToasts(prev => [...prev, { ...data, toastId, leaving: false }])

            setTimeout(() => dismiss(toastId), TOAST_LIFETIME_MS)
        })

        return () => socket.disconnect()
    }, [])

    if (toasts.length === 0) return null

    return (
        <div className="notification-toast-stack">
            {toasts.map(toast => (
                <div
                    className={`notification-toast ${toast.leaving ? 'notification-toast--leaving' : ''}`}
                    key={toast.toastId}
                >
                    <span className="notification-toast-message">{toast.message}</span>
                    <button
                        className="notification-toast-close"
                        onClick={() => dismiss(toast.toastId)}
                        aria-label="Dismiss"
                    >
                        ×
                    </button>
                </div>
            ))}
        </div>
    )
}

export default NotificationToast
