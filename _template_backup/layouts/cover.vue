<template>
  <div class="slidev-layout cover">
    <div class="cover-band">
      <h1>{{ $frontmatter.coverTitle || $frontmatter.title }}</h1>
    </div>
    <div class="cover-meta">
      <slot />
    </div>
    <div class="cover-footer">
      <div class="date">{{ $frontmatter.date }}<template v-if="$frontmatter.author"> | {{ $frontmatter.author }}</template></div>
      <!-- logo: frontmatter image path if given, else fall back to org text -->
      <img v-if="$frontmatter.logo" :src="$frontmatter.logo" class="logo-img" />
      <div v-else class="logo">{{ $frontmatter.org || 'AAiL' }}</div>
    </div>
  </div>
</template>
