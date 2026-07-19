"""1D U-Net-style delineation backbone with a heteroscedastic landmark head.

- Segmentation head: per-sample 4-class logits (bg, P, QRS, T), full input
  resolution, via encoder-decoder with skip connections.
- Landmark head: from the bottleneck features, regress (mu, log_var,
  presence_logit) for each of 4 landmarks (P-onset, QRS-onset, QRS-offset,
  T-offset), each expressed as a sample offset from the window start.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F

N_SEG_CLASSES = 4
LANDMARKS = ["p_onset", "qrs_onset", "qrs_offset", "t_offset"]
N_LANDMARKS = len(LANDMARKS)


def conv_block(c_in, c_out, k=7):
    return nn.Sequential(
        nn.Conv1d(c_in, c_out, k, padding=k // 2),
        nn.BatchNorm1d(c_out),
        nn.ReLU(inplace=True),
        nn.Conv1d(c_out, c_out, k, padding=k // 2),
        nn.BatchNorm1d(c_out),
        nn.ReLU(inplace=True),
    )


class ECGDelineator(nn.Module):
    def __init__(self, in_ch=1, base=32, depth=4, win_len=500):
        super().__init__()
        self.depth = depth
        self.win_len = win_len
        chs = [base * (2 ** i) for i in range(depth + 1)]  # e.g. 32,64,128,256,512

        self.enc_blocks = nn.ModuleList()
        c_prev = in_ch
        for c in chs[:-1]:
            self.enc_blocks.append(conv_block(c_prev, c))
            c_prev = c
        self.pool = nn.MaxPool1d(2)

        self.bottleneck = conv_block(chs[-2], chs[-1])

        self.up_convs = nn.ModuleList()
        self.dec_blocks = nn.ModuleList()
        c_prev = chs[-1]
        for c in reversed(chs[:-1]):
            self.up_convs.append(nn.ConvTranspose1d(c_prev, c, 2, stride=2))
            self.dec_blocks.append(conv_block(c * 2, c))
            c_prev = c

        self.seg_out = nn.Conv1d(chs[0], N_SEG_CLASSES, 1)

        bott_dim = chs[-1]
        self.landmark_mlp = nn.Sequential(
            nn.AdaptiveAvgPool1d(1),
            nn.Flatten(),
            nn.Linear(bott_dim, 256),
            nn.ReLU(inplace=True),
            nn.Linear(256, N_LANDMARKS * 3),  # mu, log_var, presence_logit
        )

    def forward(self, x):
        # x: (B, 1, L)
        skips = []
        h = x
        for blk in self.enc_blocks:
            h = blk(h)
            skips.append(h)
            h = self.pool(h)
        h = self.bottleneck(h)
        bott = h

        for up, dec, skip in zip(self.up_convs, self.dec_blocks, reversed(skips)):
            h = up(h)
            if h.shape[-1] != skip.shape[-1]:
                h = F.interpolate(h, size=skip.shape[-1])
            h = torch.cat([h, skip], dim=1)
            h = dec(h)

        seg_logits = self.seg_out(h)  # (B, 4, L)

        lm = self.landmark_mlp(bott)  # (B, N_LANDMARKS*3)
        lm = lm.view(-1, N_LANDMARKS, 3)
        mu = lm[..., 0]
        log_var = lm[..., 1]
        presence_logit = lm[..., 2]
        return seg_logits, mu, log_var, presence_logit
