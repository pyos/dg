```dg
import '/asyncio'

main = async $ loop ->
  task = "Hello, {}!".format whatever where
    await asyncio.sleep 1
    whatever = "World"

  await task

loop = asyncio.get_event_loop!
loop.run_until_complete $ main loop
```
