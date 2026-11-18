<template>
  <div class="slidev-layout cover">
    <div class="cover-band">
      <h1 ref="titleEl">{{ title }}</h1>
    </div>
    <div class="cover-meta">
      <slot />
    </div>
    <div class="cover-footer">
      <div class="date">{{ $frontmatter.date }}<template v-if="$frontmatter.author"> | {{ $frontmatter.author }}</template></div>
      <!-- logo: image path from `logo:`, else the `org:` text. Both omitted
           (the default) means no logo is drawn at all. -->
      <img v-if="$frontmatter.logo" :src="$frontmatter.logo" class="logo-img" />
      <div v-else-if="$frontmatter.org" class="logo">{{ $frontmatter.org }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useSlideContext } from '@slidev/client'

const { $frontmatter } = useSlideContext()
const title = computed(() => $frontmatter.coverTitle || $frontmatter.title)

/* Auto-fit the cover title.
   The band is ~852px wide and the title length varies, so rather than hard-coding
   a font-size we start at the designed size and step down until the text fits in
   MAX_LINES. Keeps short titles large and stops long ones from spilling to a
   third line, independent of which font actually resolved. */
const MAX_REM = 3.2
const MIN_REM = 1.5
const STEP_REM = 0.05
const MAX_LINES = 2

const titleEl = ref(null)

async function fitTitle() {
  const el = titleEl.value
  if (!el) return
  await nextTick()
  for (let size = MAX_REM; size >= MIN_REM; size -= STEP_REM) {
    el.style.fontSize = `${size.toFixed(2)}rem`
    const lineHeight = parseFloat(getComputedStyle(el).lineHeight)
    if (!Number.isFinite(lineHeight)) break
    // +1px of slack for sub-pixel rounding
    if (el.scrollHeight <= lineHeight * MAX_LINES + 1) break
  }
}

onMounted(() => {
  fitTitle()
  // Web fonts can land after mount and change the metrics — refit when they do.
  if (typeof document !== 'undefined' && document.fonts?.ready)
    document.fonts.ready.then(fitTitle)
})
watch(title, fitTitle)
</script>
