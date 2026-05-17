# frontend-admin 测试

```
tests/
├── unit/             # Vitest, jsdom, MSW
├── integration/      # 页面级（pages/*.vue + router + store + MSW）
├── e2e/              # Playwright，关键路径冒烟
└── fixtures/
```

跑测试：
```
pnpm test            # vitest run
pnpm test:watch      # vitest watch
pnpm test:e2e        # playwright
```
