<script setup lang="ts">
import type { B24Frame } from '@bitrix24/b24jssdk'
import { onMounted, getCurrentInstance } from 'vue'
import { useDashboard } from '@bitrix24/b24ui-nuxt/utils/dashboard'

const { t, locales: localesI18n, setLocale } = useI18n()

useHead({
  title: t('page.index.seo.title')
})

// region Init ////
const { $logger, initApp, processErrorGlobal } = useAppInit('IndexPage')
const { $initializeB24Frame } = useNuxtApp()
let $b24: null | B24Frame = null

const apiStore = useApiStore()
const robotRegistrationStatus = ref<'idle' | 'success' | 'error'>('idle')
const robotRegistrationMessage = ref('')
// endregion ////

// region Actions ////
async function getEnums() {
  const enums = await apiStore.getEnum()

  $logger.info(enums)
}

async function getItems() {
  const items = await apiStore.getList()

  $logger.info(items)
}

async function registerRobots() {
  try {
    const response = await apiStore.registerRobots()
    const registeredRobots = Array.isArray(response?.registered_robots)
      ? response.registered_robots
      : []

    robotRegistrationStatus.value = 'success'
    robotRegistrationMessage.value = registeredRobots.length > 0
      ? `Роботы зарегистрированы: ${registeredRobots.map((item: { code: string }) => item.code).join(', ')}`
      : 'Запрос выполнен, но сервер не вернул список роботов'

    $logger.info('Robots registered', response)
  } catch (error) {
    robotRegistrationStatus.value = 'error'
    robotRegistrationMessage.value = error instanceof Error
      ? error.message
      : String(error)

    $logger.error('Robot registration failed', error)
  }
}
// endregion ////

const { contextId, isLoading: isLoadingState, load } = useDashboard({ isLoading: ref(false), load: () => {} })
const isLoading = computed({
  get: () => isLoadingState?.value === true,
  set: (value: boolean) => {
    $logger.info(load, value, contextId, isLoadingState?.value)
    load?.(value, contextId)
  }
})

// region Lifecycle Hooks ////
const isInit = ref(false)
onMounted(async () => {
  $logger.info('Hi from index page')

  try {
    isLoading.value = true
    $b24 = await $initializeB24Frame()
    await initApp($b24, localesI18n, setLocale)
    await registerRobots()

    await $b24.parent.setTitle(t('page.index.seo.title'))

    isInit.value = true
  } catch (error) {
    processErrorGlobal(error)
  } finally {
    isLoading.value = false
  }
})
// endregion ////
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-16 h-[calc(100vh-200px)]">
    <B24Card
      v-if="isInit"
      :b24ui="{
        footer: 'flex flex-row flex-wrap items-center justify-start gap-2'
      }"
    >
      <template #header>
        <ProseH2>{{ $t('page.index.message.title') }}</ProseH2>
        <ProseP>{{ $t('page.index.message.line1') }}</ProseP>
      </template>

      <BackendStatus />
      <B24Alert
        v-if="robotRegistrationStatus !== 'idle'"
        :title="robotRegistrationStatus === 'success' ? 'Роботы Bitrix24' : 'Ошибка регистрации роботов'"
        :color="robotRegistrationStatus === 'success' ? 'air-primary-success' : 'air-primary-alert'"
        :description="robotRegistrationMessage"
        size="sm"
      />

      <template #footer>
        <B24Button label="Зарегистрировать роботов повторно" loading-auto @click="registerRobots" />
        <B24Button label="getEnums" loading-auto @click="getEnums" />
        <B24Button label="getItems" loading-auto @click="getItems" />
      </template>
    </B24Card>
  </div>
</template>
