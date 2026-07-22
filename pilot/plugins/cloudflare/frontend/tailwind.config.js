import frappeUIPreset from 'frappe-ui/tailwind'

/** @type {import('tailwindcss').Config} */
export default {
  presets: [frappeUIPreset],
  content: ['./src/**/*.{vue,js}', './node_modules/frappe-ui/src/**/*.{vue,js,ts}'],
}
