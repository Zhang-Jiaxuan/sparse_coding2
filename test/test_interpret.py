import os
import pickle
import sys
import unittest
# set the path to the root of the project
from copy import deepcopy
from transformers import LlamaTokenizer
from transformers import LlamaForCausalLM

from sae_lens import SAE

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from datasets import load_dataset
from transformer_lens import HookedTransformer
import torch

from activation_dataset import make_tensor_name
from autoencoders.learned_dict import TiedSAE, UntiedSAE
from config import InterpArgs
from interpret import make_feature_activation_dataset


class TestMain(unittest.TestCase):
    def setUp(self) -> None:
        os.makedirs("tmp", exist_ok=True)
        self.default_cfg = InterpArgs()

    def test_l1_mlp(self):
        cfg = deepcopy(self.default_cfg)
        self.layer = 0
        cfg.model_name = "/root/data/sae/LLMmodel/XuanYuan-6B-Chat"
        tokenizer = LlamaTokenizer.from_pretrained(cfg.model_name)
        hf_model = LlamaForCausalLM.from_pretrained(cfg.model_name, low_cpu_mem_usage=True,device_map="auto")
        # make new learned dict in a temporary folder
        mlp_dim = 4096
        feat_dim = 131072
        # ld = UntiedSAE(encoder = torch.randn(feat_dim, mlp_dim) / mlp_dim, encoder_bias=torch.rand(feat_dim) - 1, decoder=torch.randn(feat_dim, mlp_dim))
        # torch.save(ld, os.path.join("tmp", "ld.pt"))

        self.sentence_dataset = load_dataset(path="/root/data/sae/dataset/FinCorpus", split="train", streaming=True)

        # self.model = HookedTransformer.from_pretrained(cfg.model_name)
        sae_path="/root/data/sae/sae_checkpoint/uu7cllm1/final_40960000"
        self.sae  = SAE.load_from_pretrained(sae_path,device="cuda")
        self.model = HookedTransformer.from_pretrained(
            cfg.model_name,
            hf_model=hf_model,
            device="cuda",
            fold_ln=False,
            center_writing_weights=False,
            center_unembed=False,
            tokenizer=tokenizer,
            n_devices=4
        )
        self.df = make_feature_activation_dataset(
            model=self.model,
            layer=self.layer,
            layer_loc="mlpout",
            learned_dict=self.sae ,
            device="cuda",
            n_fragments=3,
            random_fragment=False,
            max_features=10
        )
        
        tensor_name = f"blocks.{self.layer}.hook_mlp_out"
        sentence = next(iter(self.sentence_dataset))["text"]
        tokens = self.model.to_tokens(sentence)[0, 1:65]
        _, cache = self.model.run_with_cache(tokens)
        mlp_activation_data = cache[tensor_name].to("cuda")[0]
        feature_activations = self.sae.encode(mlp_activation_data)
        print(self.df.keys)
        # for position in [0, 10, 63]:
        #     print(f"Testing position {position}")
        #     activations = feature_activations[position]
        #     for feature in range(feat_dim):
        #         print("test\n",self.df[f"feature_{feature}_activation_{position}"])
        #         assert (
        #             abs(self.df[f"feature_{feature}_activation_{position}"] - activations[feature]) < 1e-2
        #         ), f"feature {feature} does not match. Got {self.df[f'feature_{feature}_activation_{position}'][0]} but expected {activations[feature]}"
                       
    '''
    def test_l2_residual(self):
        cfg = deepcopy(self.default_cfg)
        self.layer = 2
        cfg.model_name = "EleutherAI/pythia-70m-deduped"
        cfg.layer_loc = "residual"
        
        # make new learned dict in a temporary folder
        feat_dim = 256
        residual_dim = 512
        ld = TiedSAE(encoder = torch.randn(feat_dim, residual_dim) / residual_dim, encoder_bias=torch.rand(feat_dim)-1)
        os.makedirs("tmp", exist_ok=True)
        torch.save(ld, os.path.join("tmp", "ld.pt"))


        self.sentence_dataset = load_dataset("openwebtext", split="train", streaming=True)
        self.model = HookedTransformer.from_pretrained(cfg.model_name)

        self.df = make_feature_activation_dataset(
            model=self.model,
            layer=self.layer,
            layer_loc=cfg.layer_loc,
            learned_dict=ld,
            device="cuda",
            n_fragments=3,
            random_fragment=False,
        )

        tensor_name = make_tensor_name(self.layer, cfg.layer_loc, model_name=self.model.cfg.model_name)
        sentence = next(iter(self.sentence_dataset))["text"]
        tokens = self.model.to_tokens(sentence)[0, 1:65]
        _, cache = self.model.run_with_cache(tokens)
        activation_data = cache[tensor_name].to("cuda")[0]
        feature_activations = ld.encode(activation_data)
        for position in [0, 10, 63]:
            print(f"Testing position {position}")
            activations = feature_activations[position]
            for feature in range(feat_dim):
                assert (
                    abs(self.df[f"feature_{feature}_activation_{position}"][0] - activations[feature]) < 1e-3
                    or abs(1 - (self.df[f"feature_{feature}_activation_{position}"][0] / activations[feature])) < 1e-3
                ), f"feature {feature} does not match. Got {self.df[f'feature_{feature}_activation_{position}'][0]} but expected {activations[feature]}"
    '''
    def tearDown(self) -> None:
        # delete temporary folder
        # os.remove(os.path.join("tmp", "ld.pt"))
        os.removedirs("tmp")
        torch.cuda.empty_cache()
        return super().tearDown()


if __name__ == "__main__":
    unittest.main()
