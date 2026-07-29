<template>
  <div class="min-h-screen w-screen bg-gradient-to-br from-blue-900 via-purple-900 to-pink-800 flex items-center justify-center p-4 relative overflow-hidden">
    <!-- Animated Background Gradients -->
    <div class="absolute -top-40 -left-40 w-96 h-96 bg-blue-500/30 rounded-full blur-3xl animate-pulse"></div>
    <div class="absolute top-1/2 left-1/2 w-96 h-96 bg-purple-500/20 rounded-full blur-3xl animate-pulse" style="animation-delay: 1s"></div>
    <div class="absolute -bottom-40 -right-40 w-96 h-96 bg-pink-500/30 rounded-full blur-3xl animate-pulse" style="animation-delay: 2s"></div>

    <!-- Login Card Container -->
    <div class="w-full max-w-md bg-white/95 backdrop-blur-xl border border-white/20 rounded-3xl p-8 shadow-2xl relative z-10">
      
      <!-- Brand Logo & Header -->
      <div class="text-center space-y-3 mb-8">
        <div class="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-gradient-to-br from-blue-600 via-purple-600 to-pink-600 text-white font-extrabold text-3xl shadow-2xl shadow-purple-500/40 tracking-wider animate-pulse">
          🎓
        </div>
        <div>
          <h1 class="text-3xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent tracking-tight">Black Building Academy</h1>
          <p class="text-sm font-semibold text-purple-600 mt-2 uppercase tracking-wider">Tuition Management Portal</p>
        </div>
      </div>

      <!-- Error Alert -->
      <div
        v-if="errorMessage"
        class="mb-6 p-4 bg-red-50 border-2 border-red-300 rounded-xl text-red-700 text-sm flex items-center gap-3 shadow-md"
      >
        <FeatherIcon name="alert-circle" class="w-5 h-5 flex-shrink-0 text-red-600" />
        <span class="font-medium">{{ errorMessage }}</span>
      </div>

      <!-- Login Form -->
      <form @submit.prevent="handleLogin" class="space-y-6">
        <div>
          <label class="block text-sm font-bold text-gray-800 mb-2">Username / Email</label>
          <div class="relative">
            <FeatherIcon name="user" class="w-5 h-5 text-purple-600 absolute left-4 top-1/2 -translate-y-1/2" />
            <input
              v-model="email"
              type="text"
              required
              placeholder="Enter your User ID or Email"
              class="w-full pl-12 pr-4 py-3.5 text-base bg-gray-50 border-2 border-gray-300 rounded-xl text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all font-medium"
            />
          </div>
        </div>

        <div>
          <label class="block text-sm font-bold text-gray-800 mb-2">Password</label>
          <div class="relative">
            <FeatherIcon name="lock" class="w-5 h-5 text-purple-600 absolute left-4 top-1/2 -translate-y-1/2" />
            <input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              required
              placeholder="••••••••"
              class="w-full pl-12 pr-12 py-3.5 text-base bg-gray-50 border-2 border-gray-300 rounded-xl text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all font-medium"
            />
            <button
              type="button"
              @click="showPassword = !showPassword"
              class="absolute right-4 top-1/2 -translate-y-1/2 text-gray-600 hover:text-purple-600 transition-colors"
            >
              <FeatherIcon :name="showPassword ? 'eye' : 'eye-off'" class="w-5 h-5" />
            </button>
          </div>
        </div>

        <button
          type="submit"
          :disabled="loading"
          class="w-full py-4 px-4 bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 hover:from-blue-700 hover:via-purple-700 hover:to-pink-700 text-white font-bold text-base rounded-xl shadow-xl shadow-purple-500/50 transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 transform hover:scale-105"
        >
          <FeatherIcon v-if="loading" name="loader" class="w-5 h-5 animate-spin" />
          <span>{{ loading ? 'Signing in...' : 'Sign In to Portal' }}</span>
        </button>
      </form>

      <!-- Footer Info -->
      <div class="mt-8 text-center text-sm text-gray-600 border-t border-gray-200 pt-6 font-medium">
        Black Building Academy © {{ new Date().getFullYear() }} • All rights reserved
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { session } from '@/data/session'

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
