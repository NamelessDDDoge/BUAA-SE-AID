import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  const theme = ref(localStorage.getItem('app_theme') || 'light')

  watch(theme, (newTheme) => {
    localStorage.setItem('app_theme', newTheme)
  })

  const toggleTheme = () => {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
  }

  const setTheme = (newTheme: string) => {
    theme.value = newTheme
  }

  return {
    theme,
    toggleTheme,
    setTheme
  }
}) 