import React, { useState, useEffect, useContext } from 'react'
import { request, formatMoney } from 'modules/Base'
import { UserPreviewCtx } from 'modules/Dashboard'

import b92 from 'assets/pictures/guns/b_92.png'
import g19C from 'assets/pictures/guns/g19_c.png'
import krasny47 from 'assets/pictures/guns/krasny_47.png'
import apex15 from 'assets/pictures/guns/apex_15.png'
import a1Augmented from 'assets/pictures/guns/a1_augmented.png'
import markovSvm from 'assets/pictures/guns/markov_svm.png'
import whisper from 'assets/pictures/guns/whisper.png'
import intervention from 'assets/pictures/guns/intervention.png'

const GUN_IMAGES = {
    b_92: b92,
    g19_c: g19C,
    krasny_47: krasny47,
    apex_15: apex15,
    a1_augmented: a1Augmented,
    markov_svm: markovSvm,
    whisper: whisper,
    intervention: intervention,
}

function Guns() {
    const [guns, setGuns] = useState(null)
    const { updateUserPreviewData } = useContext(UserPreviewCtx)

    useEffect(() => {
        getGunsData()
    }, [])

    const getGunsData = () => {
        request({ url: 'items/get_user_guns', method: 'POST' })
            .then(response => setGuns(response.data))
            .catch(error => console.error('Error getting guns data:', error))
    }

    const buyGun = (gunKey) => {
        request({ url: 'items/buy_gun', method: 'POST', data: { gun_name: gunKey } })
            .then(() => {
                alert('Gun purchased successfully')
                updateUserPreviewData()
                getGunsData()
            })
            .catch(error => alert(error.response.data.message))
    }

    const sellGun = (gunKey) => {
        request({ url: 'items/sell_gun', method: 'POST', data: { gun_name: gunKey } })
            .then(() => {
                alert('Gun sold successfully')
                updateUserPreviewData()
                getGunsData()
            })
            .catch(error => alert(error.response.data.message))
    }

    const equipGun = (gunKey) => {
        request({ url: 'items/equip_gun', method: 'POST', data: { gun_name: gunKey } })
            .then(() => {
                updateUserPreviewData()
                getGunsData()
            })
            .catch(error => alert(error.response.data.message))
    }

    const unequipGun = () => {
        request({ url: 'items/unequip_gun', method: 'POST' })
            .then(() => {
                updateUserPreviewData()
                getGunsData()
            })
            .catch(error => alert(error.response.data.message))
    }

    if (guns === null) {
        return <div className="loading-text">LOADING...</div>
    }

    return (
        <div>
            {Object.keys(guns).map(gunKey => {
                const gun = guns[gunKey]
                const owned = gun.count > 0
                const equipped = gun.is_equipped

                return (
                    <div className={`item-card ${equipped ? 'item-card--equipped' : ''}`} key={gunKey}>
                        <img className="gun-image" src={GUN_IMAGES[gunKey]} alt={gun.name} />
                        <div className="item-info">
                            <h2>
                                {gun.name}
                                {equipped && <span className="item-equipped-badge">EQUIPPED</span>}
                            </h2>
                            <div className="item-owned-cities">
                                <span>Owned: </span>
                                <span style={{ color: owned ? '#66bb6a' : undefined, fontWeight: 'bold' }}>
                                    {gun.count}
                                </span>
                            </div>
                            <p>Price: <strong className="item-price-value">{formatMoney(gun.price)}</strong></p>
                            <p>Attack: {gun.attack_multiplier}x</p>

                            <div className="item-action-row">
                                <button className="btn-buy" onClick={() => buyGun(gunKey)}>Buy</button>
                                {owned && !equipped && (
                                    <button className="btn-equip" onClick={() => equipGun(gunKey)}>
                                        Equip
                                    </button>
                                )}
                                {equipped && (
                                    <button className="btn-unequip" onClick={() => unequipGun()}>
                                        Unequip
                                    </button>
                                )}
                                {owned && (
                                    <button className="btn-sell" onClick={() => sellGun(gunKey)}>Sell</button>
                                )}
                            </div>
                        </div>
                    </div>
                )
            })}
        </div>
    )
}

export default Guns