import sys
import unittest

from mcp import Client, StdioServerParameters

from machine_cad.cli import project_root


class MCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stdio_build_measure_images_and_export_gate(self):
        root = project_root()
        params = StdioServerParameters(command=sys.executable,
                                       args=["-m", "machine_cad.mcp_server"],
                                       env={"MACHINE_CAD_ROOT": str(root), "PYTHONPATH": str(root / "src")})
        async with Client(params) as client:
            tools = await client.list_tools()
            names = {tool.name for tool in tools.tools}
            self.assertTrue({"build_model", "check_model", "inspect_model", "measure_part", "render_views", "export_files"} <= names)
            built = await client.call_tool("build_model", {"label": "mcp-test"})
            self.assertFalse(built.is_error, built.content)
            data = built.structured_content
            self.assertEqual(data["status"], "pass")
            build_id = data["build_id"]
            measured = await client.call_tool("measure_part", {"part_name": "carriage_plate", "build_id": build_id})
            self.assertFalse(measured.is_error)
            self.assertEqual(measured.structured_content["local_bounds"]["size_mm"], [100.0, 200.0, 8.0])
            images = await client.call_tool("render_views", {"build_id": build_id, "view": "all"})
            self.assertFalse(images.is_error, images.content)
            self.assertEqual(len(images.content), 6)
            self.assertTrue(all(image.type == "image" and image.mime_type == "image/png" for image in images.content))
            files = await client.call_tool("export_files", {"build_id": build_id})
            self.assertFalse(files.is_error)
            self.assertTrue(any(f["path"].endswith("assembly.step") for f in files.structured_content["files"]))
            failed = await client.call_tool("build_model", {"parameter_patch": {"travel_mm": 500.0}, "label": "mcp-failed"})
            self.assertFalse(failed.is_error)
            self.assertEqual(failed.structured_content["status"], "fail")
            gate = await client.call_tool("export_files", {"build_id": failed.structured_content["build_id"]})
            self.assertTrue(gate.is_error)
            self.assertIn("Geometry checks failed", gate.content[0].text)
            escaped = await client.call_tool("inspect_model", {"build_id": "../../outside"})
            self.assertTrue(escaped.is_error)
            self.assertIn("Invalid build identifier", escaped.content[0].text)
            invalid = await client.call_tool("check_model", {"parameter_patch": {"width_mm": -1.0}})
            self.assertTrue(invalid.is_error)
            self.assertIn("width_mm", invalid.content[0].text)
