// TaskBoard screens
export const routes = [
  { path: '/login', screen: 'SignIn' },
  { path: '/board', screen: 'Board' },
  { path: '/tasks/:id', screen: 'TaskDetail' },
  { path: '/notifications', screen: 'Notifications' },
  { path: '/settings', screen: 'Settings' },
];

// Shared button: variants used across screens
export const buttonVariants = ['primary', 'ghost'];
