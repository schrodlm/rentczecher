import type { ProfileModel } from '$lib/api/client';

/* A stored profile with every criterion and preference set, its places
named the way the engine names them. */
export function storedProfile(id: string, name: string): ProfileModel {
	return {
		id,
		name,
		paused_at: null,
		portals: ['sreality', 'remax'],
		criteria: {
			offer_type: 'rent',
			estate_type: 'flat',
			place: { kind: 'obec', code: 554782, name: 'Praha', obec: null, okres: null },
			min_price: 15000,
			max_price: 30000,
			min_size_m2: 40,
			max_size_m2: 90,
			min_land_m2: null,
			dispositions: ['2+kk', '2+1']
		},
		preferences: {
			price_per_m2_weight: 10,
			disposition_weight: 20,
			preferred_dispositions: ['2+kk'],
			size_weight: 20,
			preferred_size_m2: 70,
			place_weight: 10,
			preferred_places: [{ kind: 'mestska_cast', code: 500186, name: 'Praha 7', obec: 'Praha', okres: null }],
			land_weight: 0,
			preferred_land_m2: null,
			price_weight: 40,
			preferred_price: 22000
		}
	};
}
