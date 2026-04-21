// stores/snackbar.ts
import { defineStore } from 'pinia';

type SnackbarType = 'success' | 'error' | 'warning' | 'info';

interface SnackbarState {
  show: boolean;
  message: string;
  type: SnackbarType;
  timeout: number;
}

export const useSnackbarStore = defineStore('snackbar', {
  state: (): SnackbarState => ({
    show: false,
    message: '',
    type: 'info',
    timeout: 3000,
  }),
  actions: {
    showMessage(message: string, type: SnackbarType = 'info') {
      this.show = true;
      this.message = message;
      this.type = type;
      
      // 自动关闭
      setTimeout(() => {
        this.hide();
      }, this.timeout);
    },
    hide() {
      this.show = false;
    },
  },
});