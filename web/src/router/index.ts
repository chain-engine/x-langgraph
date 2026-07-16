import { createRouter, createWebHistory } from 'vue-router'
import WorkflowList from '@/views/WorkflowList.vue'
import WorkflowEditor from '@/views/WorkflowEditor.vue'
import ChatView from '@/views/ChatView.vue'

const routes = [
  {
    path: '/',
    name: 'list',
    component: WorkflowList,
  },
  {
    path: '/editor/:name',
    name: 'editor',
    component: WorkflowEditor,
    props: true,
  },
  {
    path: '/chat',
    name: 'chat',
    component: ChatView,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
