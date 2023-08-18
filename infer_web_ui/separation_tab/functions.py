import os
import traceback

import ffmpeg
import gradio as gr
import torch

from infer_uvr5 import _audio_pre_, _audio_pre_new


def uvr(model_name, inp_root, save_root_vocal, paths, save_root_ins, agg, format0, weight_uvr5_root, tmp, config):
    infos = []
    try:
        inp_root = inp_root.strip(" ").strip('"').strip("\n").strip('"').strip(" ")
        save_root_vocal = (
            save_root_vocal.strip(" ").strip('"').strip("\n").strip('"').strip(" ")
        )
        save_root_ins = (
            save_root_ins.strip(" ").strip('"').strip("\n").strip('"').strip(" ")
        )
        if model_name == "onnx_dereverb_By_FoxJoy":
            from MDXNet import MDXNetDereverb

            pre_fun = MDXNetDereverb(15)
        else:
            func = _audio_pre_ if "DeEcho" not in model_name else _audio_pre_new
            pre_fun = func(
                agg=int(agg),
                model_path=os.path.join(weight_uvr5_root, model_name + ".pth"),
                device=config.device,
                is_half=config.is_half,
            )
        if inp_root != "":
            paths = [os.path.join(inp_root, name) for name in os.listdir(inp_root)]
        else:
            paths = [path.name for path in paths]
        for path in paths:
            inp_path = os.path.join(inp_root, path)
            need_reformat = 1
            done = 0
            try:
                info = ffmpeg.probe(inp_path, cmd="ffprobe")
                if (
                        info["streams"][0]["channels"] == 2
                        and info["streams"][0]["sample_rate"] == "44100"
                ):
                    need_reformat = 0
                    pre_fun._path_audio_(
                        inp_path, save_root_ins, save_root_vocal, format0
                    )
                    done = 1
            except Exception as e:
                print(e)
                need_reformat = 1
                traceback.print_exc()
            if need_reformat == 1:
                tmp_path = "%s/%s.reformatted.wav" % (tmp, os.path.basename(inp_path))
                os.system(
                    "ffmpeg -i %s -vn -acodec pcm_s16le -ac 2 -ar 44100 %s -y"
                    % (inp_path, tmp_path)
                )
                inp_path = tmp_path
            try:
                if done == 0:
                    pre_fun._path_audio_(
                        inp_path, save_root_ins, save_root_vocal, format0
                    )
                infos.append("%s->Success" % (os.path.basename(inp_path)))
                yield "\n".join(infos)
            except:
                infos.append(
                    "%s->%s" % (os.path.basename(inp_path), traceback.format_exc())
                )
                yield "\n".join(infos)
    except:
        infos.append(traceback.format_exc())
        yield "\n".join(infos)
    finally:
        try:
            if model_name == "onnx_dereverb_By_FoxJoy":
                del pre_fun.pred.model
                del pre_fun.pred.model_
            else:
                del pre_fun.model
                del pre_fun
        except:
            traceback.print_exc()
        print("clean_empty_cache")
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    yield "\n".join(infos)


def load_separation_tab(i18n, uvr5_names, weight_uvr5_root, tmp, config):
    with gr.Group():
        gr.Markdown(
            value=i18n(
                "人声伴奏分离批量处理， 使用UVR5模型。 <br>合格的文件夹路径格式举例： E:\\codes\\py39\\vits_vc_gpu\\白鹭霜华测试样例(去文件管理器地址栏拷就行了)。 <br>模型分为三类： <br>1、保留人声：不带和声的音频选这个，对主人声保留比HP5更好。内置HP2和HP3两个模型，HP3可能轻微漏伴奏但对主人声保留比HP2稍微好一丁点； <br>2、仅保留主人声：带和声的音频选这个，对主人声可能有削弱。内置HP5一个模型； <br> 3、去混响、去延迟模型（by FoxJoy）：<br>  (1)MDX-Net(onnx_dereverb):对于双通道混响是最好的选择，不能去除单通道混响；<br>&emsp;(234)DeEcho:去除延迟效果。Aggressive比Normal去除得更彻底，DeReverb额外去除混响，可去除单声道混响，但是对高频重的板式混响去不干净。<br>去混响/去延迟，附：<br>1、DeEcho-DeReverb模型的耗时是另外2个DeEcho模型的接近2倍；<br>2、MDX-Net-Dereverb模型挺慢的；<br>3、个人推荐的最干净的配置是先MDX-Net再DeEcho-Aggressive。"
            )
        )
        with gr.Row():
            with gr.Column():
                dir_wav_input = gr.Textbox(
                    label=i18n("输入待处理音频文件夹路径"),
                    value="E:\\codes\\py39\\test-20230416b\\todo-songs\\todo-songs",
                )
                wav_inputs = gr.File(
                    file_count="multiple", label=i18n("也可批量输入音频文件, 二选一, 优先读文件夹")
                )
            with gr.Column():
                model_choose = gr.Dropdown(label=i18n("模型"), choices=uvr5_names)
                agg = gr.Slider(
                    minimum=0,
                    maximum=20,
                    step=1,
                    label="人声提取激进程度",
                    value=10,
                    interactive=True,
                    visible=False,  # 先不开放调整
                )
                opt_vocal_root = gr.Textbox(
                    label=i18n("指定输出主人声文件夹"), value="opt"
                )
                opt_ins_root = gr.Textbox(
                    label=i18n("指定输出非主人声文件夹"), value="opt"
                )
                format0 = gr.Radio(
                    label=i18n("导出文件格式"),
                    choices=["wav", "flac", "mp3", "m4a"],
                    value="flac",
                    interactive=True,
                )

            def uvr_wrapper(model, dir_input, vocal_root, wav_dir, opt_ins_dir, agg_aux, format00):
                return uvr(model, dir_input, vocal_root, wav_dir, opt_ins_dir, agg_aux, format00, weight_uvr5_root, tmp,
                           config)

            but2 = gr.Button(i18n("转换"), variant="primary")
            vc_output4 = gr.Textbox(label=i18n("输出信息"))
            but2.click(
                uvr_wrapper,
                [
                    model_choose,
                    dir_wav_input,
                    opt_vocal_root,
                    wav_inputs,
                    opt_ins_root,
                    agg,
                    format0,
                ],
                [vc_output4],
                api_name="uvr_convert",
            )
