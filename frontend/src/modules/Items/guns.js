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
    console.log('Guns rendered')

    const [guns, setGuns] = useState(null)

    const { userPreviewData, updateUserPreviewData } = useContext(UserPreviewCtx)

    useEffect(() => {
        getGunsData()
    }, [])

    const getGunsData = () => {
        request({
            'url': 'items/get_user_guns',
            'method': 'POST',
        })
        .then(response => {
            console.log(response.data)
            setGuns(response.data)
        })
        .catch(error => {
            console.error("Error getting items tab data: ", error)
        })
    }

    const buyGun = (gunKey) => {
        request({
            'url': 'items/buy_gun',
            'method': 'POST',
            'data': {
                'gun_name': gunKey
            }
        })
        .then(response => {
            console.log(response.data)
            alert('Gun purchased successfully')
            updateUserPreviewData()
            getGunsData()
        })
        .catch(error => {
            alert(error.response.data.message)
        })
    }

    const sellGun = (gunKey) => {
        request({
            'url': 'items/sell_gun',
            'method': 'POST',
            'data': {
                'gun_name': gunKey
            }
        })
        .then(response => {
            console.log(response.data)
            alert('Gun sold successfully')
            updateUserPreviewData()
            getGunsData()
        })
        .catch(error => {
            alert(error.response.data.message)
        })
    }

    if (guns === null) {
        return <div className="loading-text">LOADING...</div>
    }

    return (
        <div>
            {Object.keys(guns).map(gunKey => (
                <div className="item-card" key={gunKey}>
                    <img
                        className="gun-image"
                        src={GUN_IMAGES[gunKey]}
                        alt={guns[gunKey].name}
                    />
                    <div className="item-info">
                        <h2>{guns[gunKey].name}</h2>
                        <div className="item-owned-cities">
                            <span>Owned in current city: </span>
                            <span style={{ color: guns[gunKey].count_in_current_city > 0 ? '#66bb6a' : undefined, fontWeight: 'bold' }}>
                                {guns[gunKey].count_in_current_city}
                            </span>
                        </div>
                        <p>Price: <strong>{formatMoney(guns[gunKey].price)}</strong></p>
                        <p>Attack: {guns[gunKey].attack_multiplier}x</p>

                        <div style={{ display: 'flex', gap: '8px' }}>
                            <button
                                className="btn-buy"
                                onClick={() => buyGun(gunKey)}>Buy</button>
                            {guns[gunKey].count_in_current_city > 0 && (
                                <button
                                    className="btn-sell"
                                    onClick={() => sellGun(gunKey)}>Sell</button>
                            )}
                        </div>
                    </div>
                </div>
            ))}
        </div>
    )
}

export default Guns