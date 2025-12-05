### STEP-1：生成命令清单（必须指定市场参数）

python app.py analyze -s {SYMBOL} --vix 18.5 --ivr 65 --iv30 42.8 --hv20 38.2```

#### → 创建缓存 {SYMBOL + datetime}.json，包含 market_params 和 dyn_params

### STEP-2：完整分析（从缓存读取市场参数，无需再次指定）

```
python app.py analyze -s {SYMBOL} -f ./data/images --cache {SYMBOL + datetime}.json
```

### 增量更新

```
python app.py analyze -s {SYMBOL} -f ./data/images --mode update --cache {SYMBOL + datetime}.json
```

### 刷新快照

```
python app.py refresh -s {SYMBOL} -f ./data/images --cache {SYMBOL + datetime}.json
```

### 数据流向

```
app.py (analyze/refresh)
    ↓ 从缓存加载 market_params + dyn_params
    ↓ 存入 env_vars
command.execute()
    ↓ 传递 market_params, dyn_params
engine.run()
    ↓ 传递给模式处理器
mode.execute(symbol, data_folder, state, market_params, dyn_params)
    ↓ 
pipeline / code_nodes (使用展开后的 env_vars)
```

```

```
