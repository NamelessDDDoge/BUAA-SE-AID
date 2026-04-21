# Resume Training

`train.py` now supports resuming from a saved checkpoint with optimizer state.

Supported resume state:

- `model_state_dict`
- `optimizer_state_dict`
- `epoch`

Behavior:

- Training resumes from `checkpoint_epoch + 1`
- `--epochs` means the final target epoch, not "extra epochs"
- If `--logs-dir` is omitted during resume, logs continue in the same training run directory as the checkpoint

Example for this workspace:

```powershell
cd C:\Users\admin\Desktop\SE\BUAA-SE-AID\AIDetector\code\ai-training\ai-training-code\URN
conda run -n detect python train.py `
  --train-set train_splicing `
  --test-set test_splicing `
  --batch-size 4 `
  --epochs 20 `
  --resume-checkpoint "C:\Users\admin\Desktop\SE\BUAA-SE-AID\AIDetector\code\ai-training\ai-training-code\URN\logs\full_train_20260419_225556\checkpoints\latest.pkl"
```

Notes:

- The provided `latest.pkl` currently records `epoch=10`
- So `--epochs 20` resumes from epoch `11` and trains through epoch `20`
- If you want 20 more epochs beyond epoch 10, use `--epochs 30`

For `Fine` model initialization from a separate coarse checkpoint, you can also pass:

```powershell
--coarse-checkpoint "path\\to\\coarse_checkpoint.pkl"
```
