<script lang="ts">
  import './App.css'
  import { getHealth} from './api'

  let healthPromise = getHealth()

</script>

{#await healthPromise}
    <div>Checking</div>
  {:then}
    <div>Healthy</div>
  {:catch error}
    <div>{error}</div>
{/await}
