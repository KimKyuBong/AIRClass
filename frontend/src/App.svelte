<script>
  import Router from 'svelte-spa-router';
  import Teacher from './pages/Teacher.svelte';
  import Student from './pages/Student.svelte';
  import Monitor from './pages/Monitor.svelte';

  const routes = {
    '/': Student,
    '/teacher': Teacher,
    '/student': Student,
    '/monitor': Monitor,
  };
</script>

<Router {routes} />
