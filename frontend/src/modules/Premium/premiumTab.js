import React, { useContext, useState } from 'react'
import { request } from 'modules/Base'
import { UserPreviewCtx } from 'modules/Dashboard'

const MEMBER_PRIVILEGES = [
    'Create Seals — binding contracts between Elites, automatically enforced by the game',
    'Sign Seals sent to you by other Premium members',
    'Early access to future features',
]

function PremiumTab() {
    const { userPreviewData, updateUserPreviewData } = useContext(UserPreviewCtx)
    const [isSubmitting, setIsSubmitting] = useState(false)

    const isPremium = userPreviewData?.is_premium

    const handleSubscribe = () => {
        if (isSubmitting) return
        setIsSubmitting(true)

        request({ url: 'users/subscribe_premium', method: 'POST' })
            .then(res => {
                alert(res.data.message)
                updateUserPreviewData()
            })
            .catch(err => {
                alert(err.response?.data?.message || 'The request could not be completed.')
            })
            .finally(() => setIsSubmitting(false))
    }

    const handleCancel = () => {
        if (isSubmitting) return
        setIsSubmitting(true)

        request({ url: 'users/cancel_premium', method: 'POST' })
            .then(res => {
                alert(res.data.message)
                updateUserPreviewData()
            })
            .catch(err => {
                alert(err.response?.data?.message || 'The request could not be completed.')
            })
            .finally(() => setIsSubmitting(false))
    }

    return (
        <div className="premium-tab">
            <div className="premium-card">
                <div className="premium-card-crest">✦</div>
                <h2 className="premium-card-title">MEMBERSHIP</h2>
                <p className="premium-card-subtitle">
                    Certain features are available only to Premium members.
                </p>

                <div className="premium-price-line">
                    <span className="premium-price">$4.99</span>
                    <span className="premium-price-period">/ month</span>
                </div>

                <ul className="premium-privileges">
                    {MEMBER_PRIVILEGES.map((line, i) => (
                        <li key={i}>
                            <span className="premium-privilege-mark">✦</span>
                            {line}
                        </li>
                    ))}
                </ul>

                {isPremium ? (
                    <>
                        <div className="premium-active-note">
                            Your membership is active.
                        </div>
                        <button
                            className="btn-premium-cancel"
                            disabled={isSubmitting}
                            onClick={handleCancel}
                        >
                            TERMINATE MEMBERSHIP
                        </button>
                    </>
                ) : (
                    <button
                        className="btn-primary-action"
                        disabled={isSubmitting}
                        onClick={handleSubscribe}
                    >
                        {isSubmitting ? 'CONFIRMING...' : 'CONFIRM MEMBERSHIP'}
                    </button>
                )}
            </div>
        </div>
    )
}

export default PremiumTab
