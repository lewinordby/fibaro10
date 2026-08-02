import unittest

import numpy as np
import torch

from app.model import PatchCoreModel


class PositionAwarePatchCoreTests(unittest.TestCase):
    def test_patch_cannot_match_an_unrelated_atlas_position(self):
        query = torch.tensor([[1.0, 0.0], [0.0, 1.0]])
        bank = torch.tensor(
            [
                [[0.0, 1.0], [1.0, 0.0]],
                [[0.1, 0.9], [0.9, 0.1]],
            ]
        )
        distances = PatchCoreModel._distances(query, bank)
        self.assertTrue(torch.all(distances > 1.2))

    def test_identical_patches_at_the_same_position_are_normal(self):
        query = torch.tensor([[1.0, 0.0], [0.0, 1.0]])
        bank = torch.stack((query, query))
        distances = PatchCoreModel._distances(query, bank)
        torch.testing.assert_close(distances, torch.zeros(2))

    def test_tensor_is_locally_normalized_and_grayscale(self):
        atlas = np.zeros((512, 512, 3), dtype=np.uint8)
        atlas[:, :256] = (20, 80, 220)
        atlas[:, 256:] = (190, 220, 245)
        tensor = PatchCoreModel._tensor(atlas)
        self.assertEqual(tuple(tensor.shape), (1, 3, 512, 512))
        # Undo ImageNet normalization to verify that all input channels match.
        red = tensor[:, 0] * 0.229 + 0.485
        green = tensor[:, 1] * 0.224 + 0.456
        blue = tensor[:, 2] * 0.225 + 0.406
        torch.testing.assert_close(red, green, atol=1e-5, rtol=0)
        torch.testing.assert_close(red, blue, atol=1e-5, rtol=0)


if __name__ == "__main__":
    unittest.main()
