<script lang="ts">
  import './App.css'
  import { getHealth, type Health } from './api'

  let data = $state<Health | null>(null)

  $effect(() => {
    getHealth().then((health) => {
      console.log(health)
      data = health
    })
  })
</script>

{#if data}
  <div class="App">{data.status}</div>
{/if}
