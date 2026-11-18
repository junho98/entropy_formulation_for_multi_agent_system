<template>
  <div class="slidev-layout default">
    <template v-if="$frontmatter.slideTitle">
      <div v-if="titleStyle === 'navy'" class="navy-title">{{ $frontmatter.slideTitle }}</div>
      <h1 v-else>{{ $frontmatter.slideTitle }}</h1>
    </template>
    <h2 v-if="$frontmatter.sub">{{ $frontmatter.sub }}</h2>
    <slot />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useSlideContext } from '@slidev/client'
const { $frontmatter } = useSlideContext()
// title style: 'navy' (header band) or 'plain' (plain h1). Default: navy.
const titleStyle = computed(() => $frontmatter.titleStyle || 'navy')
</script>
