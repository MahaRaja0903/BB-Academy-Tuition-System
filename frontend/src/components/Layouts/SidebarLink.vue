<template>
  <nav class="space-y-2">
    <router-link
      v-for="item in navigationItems"
      :key="item.to"
      :to="item.to"
      class="group flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-300 relative overflow-hidden"
      :class="[
        $route.path === item.to || ($route.path.startsWith(item.to) && item.to !== '/')
          ? item.activeClass
          : item.inactiveClass
      ]"
      :target="item.newTab ? '_blank' : '_self'"
    >
      <!-- Colorful Icon Container -->
      <div 
        class="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-transform duration-300 group-hover:scale-110 group-hover:-rotate-3"
        :class="[
          $route.path === item.to || ($route.path.startsWith(item.to) && item.to !== '/')
            ? item.iconActiveClass
            : item.iconInactiveClass
        ]"
      >
        <FeatherIcon :name="item.icon" class="w-4 h-4" />
      </div>
      
      <span v-if="!isCollapsed" class="truncate transition-transform duration-300 group-hover:translate-x-1">{{ item.label }}</span>
      
      <!-- External link indicator -->
      <FeatherIcon 
        v-if="!isCollapsed && item.newTab" 
        name="external-link" 
        class="w-3 h-3 ml-auto opacity-0 group-hover:opacity-100 transition-opacity duration-300" 
      />
    </router-link>
  </nav>
</template>

<script setup>
defineProps({
  isCollapsed: Boolean
})

const navigationItems = [
  { 
    label: 'Dashboard', to: '/', icon: 'grid', 
    activeClass: 'bg-indigo-50 text-indigo-700 shadow-sm shadow-indigo-100/50', 
    inactiveClass: 'text-gray-600 hover:bg-indigo-50 hover:text-indigo-600',
    iconActiveClass: 'bg-indigo-100 text-indigo-600',
    iconInactiveClass: 'bg-gray-100 text-gray-500 group-hover:bg-indigo-100 group-hover:text-indigo-500'
  },
  { 
    label: 'Students', to: '/students', icon: 'users',
    activeClass: 'bg-emerald-50 text-emerald-700 shadow-sm shadow-emerald-100/50', 
    inactiveClass: 'text-gray-600 hover:bg-emerald-50 hover:text-emerald-600',
    iconActiveClass: 'bg-emerald-100 text-emerald-600',
    iconInactiveClass: 'bg-gray-100 text-gray-500 group-hover:bg-emerald-100 group-hover:text-emerald-500'
  },
  { 
    label: 'Fee Invoices', to: '/fee-invoices', icon: 'file-text',
    activeClass: 'bg-amber-50 text-amber-700 shadow-sm shadow-amber-100/50', 
    inactiveClass: 'text-gray-600 hover:bg-amber-50 hover:text-amber-600',
    iconActiveClass: 'bg-amber-100 text-amber-600',
    iconInactiveClass: 'bg-gray-100 text-gray-500 group-hover:bg-amber-100 group-hover:text-amber-500'
  },
  { 
    label: 'Enquiries', to: '/student-enquiries', icon: 'help-circle',
    activeClass: 'bg-sky-50 text-sky-700 shadow-sm shadow-sky-100/50', 
    inactiveClass: 'text-gray-600 hover:bg-sky-50 hover:text-sky-600',
    iconActiveClass: 'bg-sky-100 text-sky-600',
    iconInactiveClass: 'bg-gray-100 text-gray-500 group-hover:bg-sky-100 group-hover:text-sky-500'
  },
  { 
    label: 'Payment Entries', to: '/payment-entries', icon: 'credit-card',
    activeClass: 'bg-violet-50 text-violet-700 shadow-sm shadow-violet-100/50', 
    inactiveClass: 'text-gray-600 hover:bg-violet-50 hover:text-violet-600',
    iconActiveClass: 'bg-violet-100 text-violet-600',
    iconInactiveClass: 'bg-gray-100 text-gray-500 group-hover:bg-violet-100 group-hover:text-violet-500'
  },
  { 
    label: 'Batch History', to: '/student-batch-history', icon: 'git-branch',
    activeClass: 'bg-fuchsia-50 text-fuchsia-700 shadow-sm shadow-fuchsia-100/50', 
    inactiveClass: 'text-gray-600 hover:bg-fuchsia-50 hover:text-fuchsia-600',
    iconActiveClass: 'bg-fuchsia-100 text-fuchsia-600',
    iconInactiveClass: 'bg-gray-100 text-gray-500 group-hover:bg-fuchsia-100 group-hover:text-fuchsia-500'
  },
  { 
    label: 'Admission Forms', to: '/student-admission-forms', icon: 'file-plus',
    activeClass: 'bg-orange-50 text-orange-700 shadow-sm shadow-orange-100/50', 
    inactiveClass: 'text-gray-600 hover:bg-orange-50 hover:text-orange-600',
    iconActiveClass: 'bg-orange-100 text-orange-600',
    iconInactiveClass: 'bg-gray-100 text-gray-500 group-hover:bg-orange-100 group-hover:text-orange-500'
  },
  { 
    label: 'Promotion & Demotion', to: '/promotion-demotion-report', icon: 'pie-chart', newTab: true,
    activeClass: 'bg-rose-50 text-rose-700 shadow-sm shadow-rose-100/50', 
    inactiveClass: 'text-gray-600 hover:bg-rose-50 hover:text-rose-600',
    iconActiveClass: 'bg-rose-100 text-rose-600',
    iconInactiveClass: 'bg-gray-100 text-gray-500 group-hover:bg-rose-100 group-hover:text-rose-500'
  },
  { 
    label: 'Student Wise Report', to: '/student-wise-report', icon: 'file-text',
    activeClass: 'bg-teal-50 text-teal-700 shadow-sm shadow-teal-100/50', 
    inactiveClass: 'text-gray-600 hover:bg-teal-50 hover:text-teal-600',
    iconActiveClass: 'bg-teal-100 text-teal-600',
    iconInactiveClass: 'bg-gray-100 text-gray-500 group-hover:bg-teal-100 group-hover:text-teal-500'
  },
]
</script>
