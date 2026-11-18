<template>
  <div class="slidev-layout default">
    <div class="navy-title">{{ $frontmatter.outlineTitle || 'Outline' }}</div>
    <ul class="outline-list">
      <li
        v-for="(item, i) in items"
        :key="i"
        :class="{ active: i + 1 === Number($frontmatter.active) }"
      >{{ item }}</li>
    </ul>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useSlideContext } from '@slidev/client'
const { $frontmatter } = useSlideContext()
// items come from the slide's frontmatter `items:`; falls back to a default list
const items = computed(() =>
  $frontmatter.items && $frontmatter.items.length
    ? $frontmatter.items
    : ['Section 1', 'Section 2', 'Section 3', 'Section 4']
)
</script>
