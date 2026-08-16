import React, { useState, useEffect, useRef, useCallback } from 'react'
import socketIOClient from 'socket.io-client'
import { CHAT_SOCKET_PATH, chatSocketUrl } from 'modules/Base/constants.js'
import { request } from 'modules/Base'
import { BellIcon } from 'components/icons'

function timeAgo(timestamp) {
    const seconds = Math.floor(Date.now() / 1000 - timestamp)
    if (seconds < 60) return 'just now'
    const minutes = Math.floor(seconds / 60)
    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours}h ago`
    const days = Math.floor(hours / 24)
    return `${days}d ago`
}

export function NotificationBell() {
    const [notifications, setNotifications] = useState([])
    const [unreadCount, setUnreadCount] = useState(0)
    const [open, setOpen] = useState(false)
    const wrapperRef = useRef(null)

    const loadNotifications = useCallback(() => {
        request({
            url: 'notifications/get_notifications_data',
            method: 'POST',
        }).then(response => {
            setNotifications(response.data.notifications)
            setUnreadCount(response.data.unread_count)
        })
    }, [])

    useEffect(() => {
        loadNotifications()
    }, [loadNotifications])

    // Live push — own connection to the shared /notifications namespace,
    // same pattern as the DM/elimination sockets elsewhere in the app.
    useEffect(() => {
        const token = localStorage.getItem('token')
        const socket = socketIOClient(chatSocketUrl('/notifications'), {
            path: CHAT_SOCKET_PATH,
            query: { token },
            forceNew: true,
        })

        socket.on('new_notification', (data) => {
            setNotifications(prev => [{ ...data, read: false }, ...prev].slice(0, 30))
            setUnreadCount(count => count + 1)
        })

        return () => socket.disconnect()
    }, [])

    useEffect(() => {
        function handleClickOutside(event) {
            if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
                setOpen(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    const handleNotificationClick = (notification) => {
        if (notification.read) return

        setNotifications(prev => prev.map(n => n.id === notification.id ? { ...n, read: true } : n))
        setUnreadCount(count => Math.max(0, count - 1))
        request({
            url: 'notifications/mark_read',
            method: 'POST',
            data: { notification_id: notification.id },
        }).catch(() => {})
    }

    const handleMarkAllRead = (e) => {
        e.stopPropagation()
        if (unreadCount === 0) return

        setNotifications(prev => prev.map(n => ({ ...n, read: true })))
        setUnreadCount(0)
        request({
            url: 'notifications/mark_all_read',
            method: 'POST',
        }).catch(() => {})
    }

    return (
        <div className="notification-bell-wrapper" ref={wrapperRef}>
            <div
                className={`header-nav-item bell-item ${open ? 'active' : ''}`}
                title="Notifications"
                onClick={() => setOpen(o => !o)}
                role="button"
                tabIndex={0}
            >
                <BellIcon className="bell-svg" />
                {unreadCount > 0 && (
                    <span className="notification-badge">{unreadCount > 9 ? '9+' : unreadCount}</span>
                )}
            </div>

            {open && (
                <div className="notification-dropdown-menu">
                    <div className="notification-dropdown-header">
                        <span>Notifications</span>
                        {unreadCount > 0 && (
                            <button className="notification-mark-all" onClick={handleMarkAllRead}>
                                Mark all read
                            </button>
                        )}
                    </div>

                    {notifications.length === 0 ? (
                        <p className="notification-empty">No notifications yet.</p>
                    ) : (
                        <div className="notification-list">
                            {notifications.map(n => (
                                <div
                                    key={n.id}
                                    className={`notification-row ${n.read ? '' : 'notification-row--unread'}`}
                                    onClick={() => handleNotificationClick(n)}
                                >
                                    <span className="notification-message">{n.message}</span>
                                    <span className="notification-time">{timeAgo(n.created_at)}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

export default NotificationBell
