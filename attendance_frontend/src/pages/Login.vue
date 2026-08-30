<template>
  <div class="min-h-screen w-screen bg-black flex items-center justify-center p-4">
    <div class="w-full max-w-sm bg-white rounded-2xl p-8 shadow-2xl">
      <div class="text-center space-y-3 mb-8">
        <img :src="LOGO_URL" class="w-16 h-16 rounded-2xl mx-auto shadow-lg" alt="BB Attendance Manager" />
        <div>
          <h1 class="text-2xl font-extrabold text-gray-900 tracking-tight">BB Attendance Manager</h1>
          <p class="text-xs font-bold text-brand-600 mt-1 uppercase tracking-widest">Black Building Academy</p>
        </div>
      </div>

      <div
        v-if="errorMessage"
        class="mb-5 p-3 bg-red-50 border border-red-300 rounded-xl text-red-700 text-sm flex items-center gap-2"
      >
        <FeatherIcon name="alert-circle" class="w-4 h-4 flex-shrink-0 text-red-600" />
        <span class="font-medium">{{ errorMessage }}</span>
      </div>

      <form @submit.prevent="handleLogin" class="space-y-5">
        <div>
          <label class="block text-sm font-bold text-gray-800 mb-1.5">Username / Email</label>
          <input
            v-model="email"
            type="text"
            required
            placeholder="Enter your User ID or Email"
            class="w-full px-4 py-3 text-base bg-gray-50 border-2 border-gray-300 rounded-xl text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-all"
          />
        </div>

        <div>
          <label class="block text-sm font-bold text-gray-800 mb-1.5">Password</label>
          <div class="relative">
            <input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              required
              placeholder="••••••••"
              class="w-full px-4 py-3 pr-11 text-base bg-gray-50 border-2 border-gray-300 rounded-xl text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-all"
            />
            <button
              type="button"
              @click="showPassword = !showPassword"
              class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-800"
            >
              <FeatherIcon :name="showPassword ? 'eye' : 'eye-off'" class="w-4 h-4" />
            </button>
          </div>
        </div>

        <button
          type="submit"
          :disabled="loading"
          class="w-full py-3.5 px-4 bg-black hover:bg-gray-900 text-brand-500 font-bold text-base rounded-xl shadow-lg transition-all flex items-center justify-center gap-2 disabled:opacity-50"
        >
          <FeatherIcon v-if="loading" name="loader" class="w-5 h-5 animate-spin" />
          <span>{{ loading ? 'Signing in...' : 'Sign In' }}</span>
        </button>
      </form>

      <div class="mt-7 text-center text-xs text-gray-500 border-t border-gray-200 pt-5">
        Black Building Academy © {{ new Date().getFullYear() }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { session } from '@/data/session'
import { LOGO_URL } from '@/data/assets'

const router = useRouter()
const email = ref('')
const password = ref('')
const showPassword = ref(false)
const errorMessage = ref('')
const loading = ref(false)

const handleLogin = async () => {
  if (!email.value || !password.value) return

  loading.value = true
  errorMessage.value = ''

  try {
    await session.login.submit({
      email: email.value,
      password: password.value,
    })
    router.replace('/')
  } catch (error) {
    if (error?.messages && error.messages.length > 0) {
      errorMessage.value = error.messages[0]
    } else if (error?.exc_type === 'AuthenticationError') {
      errorMessage.value = 'Invalid login credentials. Please check your username and password.'
    } else {
      errorMessage.value = error?.message || 'Login failed. Please verify credentials.'
    }
  } finally {
    loading.value = false
  }
}
</script>
