
// 参考： https://github.com/mengxiong10/react-modal-store

import { ModalContext, useModal, createModalHook } from './context';
import ModalStore from './modal-store';

export { ModalStore, ModalContext, useModal, createModalHook };


export interface BaseModalProps {
  visible: boolean;
  onCancel: () => void;
}