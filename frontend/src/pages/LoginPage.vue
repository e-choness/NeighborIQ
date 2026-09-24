<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from '@/components/ui/Button.vue'
import Field from '@/components/ui/Field.vue'
import { inputClass } from '@/components/ui/inputClass'
import Segmented from '@/components/ui/Segmented.vue'
import { useAuth } from '@/stores/auth'

const auth = useAuth()
const route = useRoute()
const router = useRouter()
const mode = ref<'login' | 'signup'>('login')
const email = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  error.value = ''
  busy.value = true
  try {
    if (mode.value === 'login') await auth.login(email.value, password.value)
    else await auth.signup(email.value, password.value)
    router.replace((route.query.next as string) || '/portfolio')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Something went wrong'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-sm pt-8">
    <h1 class="text-2xl font-semibold tracking-tight">{{ mode === 'login' ? 'Sign in' : 'Create an account' }}</h1>
    <p class="mt-1 text-sm text-text-2">Save deals with your own assumptions and compare them side by side.</p>
    <Segmented
      v-model="mode"
      class="mt-6"
      label="Account"
      :options="[{ value: 'login', label: 'Sign in' }, { value: 'signup', label: 'Create account' }]"
    />
    <form class="mt-6 space-y-4" @submit.prevent="submit">
      <Field label="Email" for="email"><input id="email" v-model="email" type="email" required autocomplete="email" :class="inputClass" /></Field>
      <Field label="Password" for="password" :hint="mode === 'signup' ? 'At least 8 characters.' : undefined">
        <input id="password" v-model="password" type="password" required minlength="8" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" :class="inputClass" />
      </Field>
      <p v-if="error" class="text-sm text-bad" role="alert">{{ error }}</p>
      <Button type="submit" class="w-full" :disabled="busy">{{ mode === 'login' ? 'Sign in' : 'Create account' }}</Button>
    </form>
  </div>
</template>
