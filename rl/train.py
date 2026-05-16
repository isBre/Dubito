"""
Train a PPO agent on DubitoEnv.

Usage:
    python rl/train.py                        # default 500k steps
    python rl/train.py --steps 2000000        # longer run
    python rl/train.py --resume rl/models/ppo_dubito.zip

The trained model is saved to rl/models/ppo_dubito.zip and periodically
checkpointed to rl/models/checkpoints/.
"""

import argparse
import os
import sys

from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import VecNormalize
from stable_baselines3.common.callbacks import (
    CheckpointCallback,
    EvalCallback,
)
from stable_baselines3.common.monitor import Monitor

# make project root importable when running from any cwd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rl.env import DubitoEnv


def _has_tb() -> bool:
    try:
        import tensorboard  # noqa: F401
        return True
    except ImportError:
        return False

MODEL_DIR  = "rl/models"
CKPT_DIR   = "rl/models/checkpoints"
MODEL_PATH = f"{MODEL_DIR}/ppo_dubito"


def make_env(rank: int = 0):
    def _init():
        env = DubitoEnv()
        env = Monitor(env)
        return env
    return _init


def train(total_steps: int, resume_path: str | None = None) -> None:
    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(CKPT_DIR,  exist_ok=True)

    STATS_PATH = f"{MODEL_DIR}/vecnormalize.pkl"

    n_envs  = min(8, os.cpu_count() or 4)
    vec_env = make_vec_env(make_env(), n_envs=n_envs)
    # VecNormalize normalises continuous observations using running mean/std
    # collected from actual games — far better than hand-tuned divisors.
    # norm_reward=False: we keep sparse ±1 rewards as-is.
    if resume_path and os.path.exists(STATS_PATH):
        vec_env = VecNormalize.load(STATS_PATH, vec_env)
        vec_env.training = True
    else:
        vec_env = VecNormalize(vec_env, norm_obs=True, norm_reward=False, clip_obs=10.0)

    eval_env = VecNormalize(
        make_vec_env(make_env(), n_envs=1),
        norm_obs=True, norm_reward=False, training=False,
    )

    if resume_path:
        print(f"Resuming from {resume_path}")
        model = PPO.load(resume_path, env=vec_env)
    else:
        model = PPO(
            policy="MlpPolicy",
            env=vec_env,
            n_steps=2048,
            batch_size=512,
            n_epochs=10,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.01,       # encourages exploration
            learning_rate=3e-4,
            policy_kwargs=dict(net_arch=[256, 256]),
            verbose=1,
            tensorboard_log="rl/logs/" if _has_tb() else None,
        )

    callbacks = [
        CheckpointCallback(
            save_freq=max(50_000 // n_envs, 1),
            save_path=CKPT_DIR,
            name_prefix="ppo_dubito",
        ),
        EvalCallback(
            eval_env,
            best_model_save_path=MODEL_DIR,
            log_path="rl/logs/eval/",
            eval_freq=max(25_000 // n_envs, 1),
            n_eval_episodes=200,
            deterministic=True,
            verbose=1,
        ),
    ]

    print(f"Training PPO for {total_steps:,} steps across {n_envs} parallel envs …")
    model.learn(total_timesteps=total_steps, callback=callbacks, reset_num_timesteps=resume_path is None)
    model.save(MODEL_PATH)
    vec_env.save(STATS_PATH)
    print(f"\nModel saved to {MODEL_PATH}.zip")
    print(f"VecNormalize stats saved to {STATS_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps",  type=int, default=500_000)
    parser.add_argument("--resume", type=str, default=None)
    args = parser.parse_args()
    train(args.steps, args.resume)
