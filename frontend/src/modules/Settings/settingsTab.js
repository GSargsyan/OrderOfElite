import React, { useState, useEffect } from 'react'
import { request } from 'modules/Base'

function SettingsTab() {
    const [email, setEmail] = useState('')
    const [loading, setLoading] = useState(true)
    const [submitting, setSubmitting] = useState(false)
    const [successMsg, setSuccessMsg] = useState('')
    const [errorMsg, setErrorMsg] = useState('')

    useEffect(() => {
        request({
            url: 'users/get_settings_tab_data',
            method: 'POST',
        })
            .then(res => {
                setEmail(res.data.email || '')
                setLoading(false)
            })
            .catch(err => {
                console.error(err)
                setLoading(false)
            })
    }, [])

    const handleSave = (e) => {
        e.preventDefault()
        setSuccessMsg('')
        setErrorMsg('')

        const trimmedEmail = email.trim()
        const emailRegex = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/

        if (trimmedEmail && !emailRegex.test(trimmedEmail)) {
            setErrorMsg('Please enter a valid email address.')
            return
        }

        setSubmitting(true)

        request({
            url: 'users/update_settings',
            method: 'POST',
            data: { email: trimmedEmail }
        })
            .then(res => {
                setSuccessMsg(res.data.message || 'Settings saved successfully.')
                setEmail(res.data.email || '')
                setSubmitting(false)
            })
            .catch(err => {
                if (err?.response?.data?.error) {
                    setErrorMsg(err.response.data.error)
                } else {
                    setErrorMsg('Failed to update settings. Please try again.')
                }
                setSubmitting(false)
            })
    }

    if (loading) {
        return <div className="settings-loading">Loading...</div>
    }

    return (
        <div className="settings-tab-panel">
            <h2 className="settings-title">Account Settings</h2>

            <form onSubmit={handleSave} className="settings-form">
                <div className="settings-field-group">
                    <label htmlFor="settings-email" className="settings-label">Email</label>
                    <input
                        id="settings-email"
                        type="text"
                        className="settings-input"
                        placeholder="name@example.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                    />
                    <span className="settings-field-hint">
                        Used only for account notifications.
                    </span>
                </div>

                {errorMsg && <div className="settings-banner error-banner">{errorMsg}</div>}
                {successMsg && <div className="settings-banner success-banner">{successMsg}</div>}

                <div className="settings-actions">
                    <button
                        type="submit"
                        className="btn-save-settings"
                        disabled={submitting}
                    >
                        {submitting ? 'Saving...' : 'Save'}
                    </button>
                </div>
            </form>
        </div>
    )
}

export default SettingsTab
