/**
 * main.ts
 *
 * Bootstraps Vuetify and other plugins then mounts the App`
 */

// Plugins
import { registerPlugins } from '@/plugins'
import '@/styles/app-shell.css'

// Components
import App from './App.vue'

// Composables
import { createApp } from 'vue'
import { APP_NAME } from '@/constants/app'

document.title = APP_NAME

const app = createApp(App)

registerPlugins(app)

app.mount('#app')
