# Configuration des canaux DMX

## Attribution manuelle des canaux

Vous pouvez éditer le fichier `entity_mappings.json` pour attribuer manuellement les canaux DMX à vos entités.

### Format du fichier

```json
{
  "entity_id": {
    "entity_id": "light.mon_ampoule",
    "entity_type": "rgbw",
    "dmx_channel": 1,
    "name": "Mon Ampoule",
    "rgb_channels": [2, 3, 4, 5]
  }
}
```

### Types d'entités

#### **switch** - Interrupteur simple
- **dmx_channel**: Canal DMX (1-512)
- **rgb_channels**: `[]` (vide)
- Comportement: ON si valeur > 125, OFF sinon

```json
{
  "entity_id": "switch.mon_interrupteur",
  "entity_type": "switch",
  "dmx_channel": 10,
  "name": "Mon Interrupteur",
  "rgb_channels": []
}
```

#### **dimmer** - Variateur de lumière
- **dmx_channel**: Canal DMX pour la luminosité (1-512)
- **rgb_channels**: `[]` (vide)
- Comportement: Luminosité 0-255

```json
{
  "entity_id": "light.ma_lampe",
  "entity_type": "dimmer",
  "dmx_channel": 15,
  "name": "Ma Lampe",
  "rgb_channels": []
}
```

#### **rgb** - Lumière RGB
- **dmx_channel**: Canal DMX pour la luminosité principale
- **rgb_channels**: `[R, G, B]` - 3 canaux consécutifs
- Comportement: 
  - Canal principal: Luminosité (0-255)
  - Canal R: Rouge (0-255)
  - Canal G: Vert (0-255)
  - Canal B: Bleu (0-255)

```json
{
  "entity_id": "light.mon_rgb",
  "entity_type": "rgb",
  "dmx_channel": 20,
  "name": "Mon RGB",
  "rgb_channels": [21, 22, 23]
}
```

#### **rgbw** - Lumière RGBW
- **dmx_channel**: Canal DMX pour la luminosité principale
- **rgb_channels**: `[R, G, B, W]` - 4 canaux consécutifs
- Comportement:
  - Canal principal: Luminosité (0-255)
  - Canal R: Rouge (0-255)
  - Canal G: Vert (0-255)
  - Canal B: Bleu (0-255)
  - Canal W: Blanc (0-255)

```json
{
  "entity_id": "light.mon_rgbw",
  "entity_type": "rgbw",
  "dmx_channel": 1,
  "name": "Mon RGBW",
  "rgb_channels": [2, 3, 4, 5]
}
```

## Exemple complet

```json
{
  "light.ampoule_salon": {
    "entity_id": "light.ampoule_salon",
    "entity_type": "rgbw",
    "dmx_channel": 1,
    "name": "Ampoule Salon",
    "rgb_channels": [2, 3, 4, 5]
  },
  "light.spot_cuisine": {
    "entity_id": "light.spot_cuisine",
    "entity_type": "dimmer",
    "dmx_channel": 10,
    "name": "Spot Cuisine",
    "rgb_channels": []
  },
  "switch.prise_tv": {
    "entity_id": "switch.prise_tv",
    "entity_type": "switch",
    "dmx_channel": 15,
    "name": "Prise TV",
    "rgb_channels": []
  },
  "light.bandeau_led": {
    "entity_id": "light.bandeau_led",
    "entity_type": "rgb",
    "dmx_channel": 20,
    "name": "Bandeau LED",
    "rgb_channels": [21, 22, 23]
  }
}
```

## Conseils

1. **Évitez les chevauchements** : Assurez-vous qu'aucun canal n'est utilisé deux fois
2. **Canaux consécutifs pour RGB/RGBW** : Les canaux de couleur doivent être dans l'ordre R, G, B, (W)
3. **Redémarrez le bridge** après modification du fichier
4. **Sauvegardez** votre configuration avant de rafraîchir les entités

## Détection automatique

Le bridge détecte automatiquement le type d'entité basé sur les `supported_color_modes` de Home Assistant :
- `rgbw` ou `rgbww` → RGBW
- `rgb` ou `hs` → RGB
- `brightness` → Dimmer
- Autres → Switch

Si la détection automatique ne fonctionne pas correctement, éditez manuellement le fichier `entity_mappings.json`.
